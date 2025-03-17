from flask import Flask, render_template_string
import json
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@app.route('/')
def index():
    try:
        with open("cached_gigs.json", "r") as f:
            gigs = json.load(f)
    except Exception as e:
        logging.error("Error loading cached gigs: " + str(e))
        gigs = []
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Upcoming Gigs</title>
        <!-- Bootstrap CSS -->
        <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body, table, th, td { text-align: center; }
            body { background-color: #f8f9fa; padding: 20px; }
            h1 { margin-bottom: 30px; }
            strong { font-weight: bold; }
            .spotify-embed iframe {
                width: 300px;
                height: 80px;
            }
            table { width: 100%; }
            /* Table header with black background and white text */
            thead.thead-dark th {
                background-color: #000 !important;
                color: #fff !important;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="text-center">Upcoming Gigs</h1>
            <table class="table table-bordered table-hover">
                <thead class="thead-dark">
                    <tr>
                        <th>Date</th>
                        <th><strong>Title</strong></th>
                        <th>Location</th>
                        <th>Spotify</th>
                        <th>Genre</th>
                    </tr>
                </thead>
                <tbody>
                    {% for gig in gigs %}
                    <tr>
                        <td>{{ gig.date }}</td>
                        <td>
                            {% if gig.social_link %}
                                <a href="{{ gig.social_link }}" target="_blank"><strong>{{ gig.title }}</strong></a>
                            {% else %}
                                <strong>{{ gig.title }}</strong>
                            {% endif %}
                        </td>
                        <td>
                            {% if gig.details_url %}
                                <a href="{{ gig.details_url }}" target="_blank">{{ gig.location }}</a>
                            {% else %}
                                {{ gig.location }}
                            {% endif %}
                        </td>
                        <td>
                            {% if gig.top_track_id %}
                                <div class="spotify-embed">
                                    <iframe src="https://open.spotify.com/embed/track/{{ gig.top_track_id }}" frameborder="0" allowtransparency="true" allow="encrypted-media"></iframe>
                                </div>
                            {% else %}
                                N/A
                            {% endif %}
                        </td>
                        <td>{{ gig.genre or "N/A" }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        <!-- Bootstrap JS and dependencies -->
        <script src="https://code.jquery.com/jquery-3.5.1.slim.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@4.5.2/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """
    return render_template_string(html_template, gigs=gigs)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
