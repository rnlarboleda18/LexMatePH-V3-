"""
Minimal HTML pages for third-party embeds. Loaded in <iframe src="/api/embeds/..."> so
Twitter widgets.js runs in a plain document (React/PWA often breaks timeline injection).
"""
import azure.functions as func

embeds_bp = func.Blueprint()

# Legacy twitter.com href is what publish.twitter.com / widgets.js expect for profile timelines.
SC_PIO_TWITTER = "https://twitter.com/SCPh_PIO"


@embeds_bp.route(route="embeds/twitter-scpio", auth_level=func.AuthLevel.ANONYMOUS)
def embed_twitter_scpio(req: func.HttpRequest) -> func.HttpResponse:
    theme = (req.params.get("theme") or "light").lower()
    if theme not in ("light", "dark"):
        theme = "light"
    html = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<style>html,body{{margin:0;background:transparent;overflow-x:hidden}}</style>
</head><body>
<a class="twitter-timeline" data-width="100%" data-height="580" data-theme="{theme}" data-chrome="noheader nofooter noborders transparent" href="{SC_PIO_TWITTER}">Posts by @SCPh_PIO</a>
<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>
</body></html>"""
    return func.HttpResponse(
        html,
        mimetype="text/html",
        status_code=200,
        headers={
            "Cache-Control": "no-store, max-age=0",
            "X-Content-Type-Options": "nosniff",
        },
    )
