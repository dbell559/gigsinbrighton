import json, base64, re, logging
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse as date_parse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# === CONFIGURATION ===
SPOTIFY_CLIENT_ID = '4bdd9daf7a154a7f869b567bf7438cbf'
SPOTIFY_CLIENT_SECRET = 'a895368b70f14c078a54199a139d04f5'
LASTFM_API_KEY = '96eeed0e4be50cf55680f6c9c6214dad'
GIGS_URL = 'https://www.rivalcults.com/gigs'
REQUEST_TIMEOUT = 5  # seconds

# === HELPER FUNCTION FOR ORDINALS ===
def ordinal(n):
    n = int(n)
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"

# === HELPER FUNCTIONS ===
def normalize_artist_name(name):
    name = name.lower().strip()
    name = re.sub(r'^(the|a|an)\s+', '', name)
    name = re.sub(r'[^a-z0-9]', '', name)
    return name

# === SPOTIFY API FUNCTIONS ===
def get_spotify_token():
    auth_url = 'https://accounts.spotify.com/api/token'
    auth_header = base64.b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()).decode()
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {'grant_type': 'client_credentials'}
    logging.info("Requesting Spotify token...")
    response = requests.post(auth_url, headers=headers, data=data, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    token = response.json()['access_token']
    logging.info("Spotify token obtained.")
    return token

def get_spotify_info(artist_name, token):
    search_url = 'https://api.spotify.com/v1/search'
    headers = {'Authorization': f'Bearer {token}'}
    params = {'q': artist_name, 'type': 'artist', 'limit': 1}
    logging.info(f"Searching Spotify for artist: {artist_name}")
    response = requests.get(search_url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    results = response.json()
    items = results.get('artists', {}).get('items', [])
    if items:
        artist_info = items[0]
        if normalize_artist_name(artist_info['name']) == normalize_artist_name(artist_name):
            artist_id = artist_info['id']
            spotify_url = artist_info['external_urls']['spotify']
            artist_detail_url = f'https://api.spotify.com/v1/artists/{artist_id}'
            detail_response = requests.get(artist_detail_url, headers=headers, timeout=REQUEST_TIMEOUT)
            detail_response.raise_for_status()
            detailed_info = detail_response.json()
            genres = detailed_info.get('genres', [])
            genres_str = ', '.join(genres) if genres else ''
            logging.info(f"Found artist: {artist_info['name']} with genres: {genres_str}")
            return spotify_url, genres_str, artist_id
    logging.warning(f"No Spotify info found for: {artist_name}")
    return '', '', None

def get_spotify_top_track(artist_id, token, market="US"):
    top_tracks_url = f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"market": market}
    logging.info(f"Retrieving top track for artist ID: {artist_id}")
    response = requests.get(top_tracks_url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    tracks = data.get("tracks", [])
    if tracks:
        top_track = tracks[0]
        track_name = top_track.get("name", "")
        track_url = top_track.get("external_urls", {}).get("spotify", "")
        logging.info(f"Top track: {track_name}")
        return track_name, track_url
    logging.warning(f"No top track found for artist ID: {artist_id}")
    return "", ""

# === LAST.FM API FUNCTIONS FOR SOCIAL LINKS (NO GOOGLE FALLBACK) ===
def get_lastfm_instagram(artist_name, api_key):
    lastfm_url = "http://ws.audioscrobbler.com/2.0/"
    params = {"method": "artist.getInfo", "artist": artist_name, "api_key": api_key, "format": "json"}
    logging.info(f"Requesting Last.fm info for artist: {artist_name}")
    response = requests.get(lastfm_url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    genre = ''
    instagram_link = ''
    if "artist" in data:
        artist_data = data["artist"]
        if "tags" in artist_data and "tag" in artist_data["tags"]:
            tag_list = artist_data["tags"]["tag"]
            tags = [tag["name"] for tag in tag_list if "name" in tag]
            genre = ", ".join(tags)
        if "url" in artist_data:
            lastfm_artist_url = artist_data["url"]
            page_response = requests.get(lastfm_artist_url, timeout=REQUEST_TIMEOUT)
            page_response.raise_for_status()
            soup = BeautifulSoup(page_response.text, 'html.parser')
            insta_link_tag = soup.find("a", href=lambda href: href and "instagram.com" in href)
            if insta_link_tag:
                instagram_link = insta_link_tag['href']
                # Discard banned Instagram channel.
                if instagram_link.lower().startswith("https://www.instagram.com/last_fm"):
                    instagram_link = ''
    return genre, instagram_link

def get_lastfm_youtube(artist_name, api_key):
    lastfm_url = "http://ws.audioscrobbler.com/2.0/"
    params = {"method": "artist.getInfo", "artist": artist_name, "api_key": api_key, "format": "json"}
    logging.info(f"Requesting Last.fm YouTube info for artist: {artist_name}")
    response = requests.get(lastfm_url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    youtube_link = ''
    if "artist" in data:
        artist_data = data["artist"]
        if "url" in artist_data:
            lastfm_artist_url = artist_data["url"]
            page_response = requests.get(lastfm_artist_url, timeout=REQUEST_TIMEOUT)
            page_response.raise_for_status()
            soup = BeautifulSoup(page_response.text, 'html.parser')
            yt_link_tag = soup.find("a", href=lambda href: href and "youtube.com" in href)
            if yt_link_tag:
                youtube_link = yt_link_tag['href']
                lower_link = youtube_link.lower()
                if lower_link.startswith("https://www.youtube.com/@lastfm") or lower_link.startswith("https://www.youtube.com/user/lastfm"):
                    youtube_link = ''
    return youtube_link

# === HTML PARSING FUNCTIONS ===
def parse_gigs(html):
    soup = BeautifulSoup(html, 'html.parser')
    gigs = []
    table = soup.find('table')
    if table:
        rows = table.find_all('tr')[1:]  # Skip header row
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 4:
                gigs.append({
                    'date': cols[0].get_text(strip=True),
                    'title': cols[1].get_text(strip=True),
                    'location': cols[2].get_text(strip=True),
                    'details_url': cols[3].find('a')['href'] if cols[3].find('a') else ''
                })
    else:
        logging.warning("No table found – please update the parsing logic.")
    return gigs

def extract_first_band(title):
    return title.split(',')[0].split('+')[0].strip()

def process_gig(gig, spotify_token):
    first_band = extract_first_band(gig['title'])
    try:
        spotify_link, genre, artist_id = get_spotify_info(first_band, spotify_token)
    except Exception as e:
        logging.error(f"Error fetching Spotify info for '{first_band}': {e}")
        spotify_link, genre, artist_id = '', '', None

    top_track_name, top_track_link = "", ""
    top_track_id = ""
    if artist_id:
        try:
            top_track_name, top_track_link = get_spotify_top_track(artist_id, spotify_token)
            if top_track_link:
                parts = top_track_link.split("/track/")
                if len(parts) > 1:
                    track_part = parts[1]
                    top_track_id = track_part.split("?")[0]
        except Exception as e:
            logging.error(f"Error fetching top track for '{first_band}': {e}")

    social_link = ''
    if spotify_link:
        try:
            lastfm_genre, instagram_link = get_lastfm_instagram(first_band, LASTFM_API_KEY)
            if not genre and lastfm_genre:
                genre = lastfm_genre
            # Prioritize Instagram: if valid, use it.
            if instagram_link:
                social_link = instagram_link
            else:
                youtube_link = get_lastfm_youtube(first_band, LASTFM_API_KEY)
                if youtube_link and not (youtube_link.lower().startswith("https://www.youtube.com/@lastfm") or 
                                         youtube_link.lower().startswith("https://www.youtube.com/user/lastfm")):
                    social_link = youtube_link
        except Exception as e:
            logging.error(f"Error fetching Last.fm social info for '{first_band}': {e}")
    gig['genre'] = genre
    gig['social_link'] = social_link
    gig['top_track_id'] = top_track_id

    try:
        dt = date_parse(gig['date'])
        gig['date'] = dt.strftime("%a") + ", " + gig['date']
        full_date = dt.strftime("%A") + ", " + str(dt.day) + " " + dt.strftime("%B")
        gig['full_date'] = full_date
        gig['day'] = dt.strftime("%A")
    except Exception as e:
        logging.error(f"Error formatting date for gig: {gig['date']}")
        gig['day'] = ""
    return gig

def get_gigs_data():
    logging.info("Fetching gigs from: " + GIGS_URL)
    response = requests.get(GIGS_URL, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    gigs = parse_gigs(response.text)
    gigs = sorted(gigs, key=lambda gig: date_parse(gig['date']))

    processed = []
    seen_days = set()
    try:
        spotify_token = get_spotify_token()
    except Exception as e:
        logging.error(f"Error obtaining Spotify token: {e}")
        return gigs

    for gig in gigs:
        try:
            dt = date_parse(gig['date'])
        except Exception as e:
            logging.error(f"Error parsing date for gig: {gig['date']}")
            continue

        if dt.date() < datetime.now().date():
            logging.info(f"Skipping past gig dated {gig['date']}")
            continue

        gig = process_gig(gig, spotify_token)
        if gig.get('day', ""):
            if gig['day'] not in seen_days:
                if len(seen_days) < 10:
                    seen_days.add(gig['day'])
                else:
                    break
        processed.append(gig)
        if len(processed) >= 100:
            break
    logging.info("Finished processing gigs.")
    return processed[:100]

if __name__ == '__main__':
    gigs = get_gigs_data()
    with open("cached_gigs.json", "w") as f:
        json.dump(gigs, f)
    logging.info("Cached gigs updated.")
