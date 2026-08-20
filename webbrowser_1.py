import webbrowser
import urllib.parse

query = "Ishikas Magic"
encoded_query = urllib.parse.quote_plus(query)
url = f"https://www.google.com/search?q={encoded_query}"

webbrowser.open(url)
