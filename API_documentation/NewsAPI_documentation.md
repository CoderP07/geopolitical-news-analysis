NewsAPI python Github link: https://github.com/mattlisiv/newsapi-python

News API has 2 main endpoints:
Everything /v2/everything – search every article published by over 150,000 different sources large and small in the last 5 years. This endpoint is ideal for news analysis and article discovery.
Top headlines /v2/top-headlines – returns breaking news headlines for countries, categories, and singular publishers. This is perfect for use with news tickers or anywhere you want to use live up-to-date news headlines.
There is also a minor endpoint that can be used to retrieve a small subset of the publishers we can scan:
Sources /v2/top-headlines/sources – returns information (including name, description, and category) about the most notable sources available for obtaining top headlines from. This list could be piped directly through to your users when showing them some of the options available.


** Everything /v2/everything **
Search through millions of articles from over 150,000 large and small news sources and blogs.
This endpoint suits article discovery and analysis.
Request parameters
apiKey
required
Your API key. Alternatively you can provide this via the X-Api-Key HTTP header.
q
Keywords or phrases to search for in the article title and body.
Advanced search is supported here:
Surround phrases with quotes (") for exact match.
Prepend words or phrases that must appear with a + symbol. Eg: +bitcoin
Prepend words that must not appear with a - symbol. Eg: -bitcoin
Alternatively you can use the AND / OR / NOT keywords, and optionally group these with parenthesis. Eg: crypto AND (ethereum OR litecoin) NOT bitcoin.
The complete value for q must be URL-encoded. Max length: 500 chars.
searchIn
The fields to restrict your q search to.
The possible options are:
title
description
content
Multiple options can be specified by separating them with a comma, for example: title,content.
This parameter is useful if you have an edge case where searching all the fields is not giving the desired outcome, but generally you should not need to set this.



Default: all fields are searched.
sources
A comma-seperated string of identifiers (maximum 20) for the news sources or blogs you want headlines from. Use the /sources endpoint to locate these programmatically or look at the sources index.
domains
A comma-seperated string of domains (eg bbc.co.uk, techcrunch.com, engadget.com) to restrict the search to.
excludeDomains
A comma-seperated string of domains (eg bbc.co.uk, techcrunch.com, engadget.com) to remove from the results.
from
A date and optional time for the oldest article allowed. This should be in ISO 8601 format (e.g. 2026-04-09 or 2026-04-09T19:13:57)



Default: the oldest according to your plan.
to
A date and optional time for the newest article allowed. This should be in ISO 8601 format (e.g. 2026-04-09 or 2026-04-09T19:13:57)



Default: the newest according to your plan.
language
The 2-letter ISO-639-1 code of the language you want to get headlines for. Possible options: ardeenesfrheitnlnoptrusvudzh.



Default: all languages returned.
sortBy
The order to sort the articles in. Possible options: relevancy, popularity, publishedAt.
relevancy = articles more closely related to q come first.
popularity = articles from popular sources and publishers come first.
publishedAt = newest articles come first.



Default: publishedAt
pageSize
int
The number of results to return per page.



Default: 100. Maximum: 100.
page
int
Use this to page through the results.



Default: 1.
Response object
status
string
If the request was successful or not. Options: ok, error. In the case of error a code and message property will be populated.
totalResults
int
The total number of results available for your request. Only a limited number are shown at a time though, so use the page parameter in your requests to page through them.
articles
array[article]
The results of the request.
source
object
The identifier id and a display name name for the source this article came from.
author
string
The author of the article
title
string
The headline or title of the article.
description
string
A description or snippet from the article.
url
string
The direct URL to the article.
urlToImage
string
The URL to a relevant image for the article.
publishedAt
string
The date and time that the article was published, in UTC (+000)
content
string
The unformatted content of the article, where available. This is truncated to 200 chars.



** Top headlines /v2/top-headlines **
This endpoint provides live top and breaking headlines for a country, specific category in a country, single source, or multiple sources. You can also search with keywords. Articles are sorted by the earliest date published first.
This endpoint is great for retrieving headlines for use with news tickers or similar.
Request parameters
apiKey
required
Your API key. Alternatively you can provide this via the X-Api-Key HTTP header.
country
The 2-letter ISO 3166-1 code of the country you want to get headlines for. Possible options: us. Note: you can't mix this param with the sources param.
category
The category you want to get headlines for. Possible options: businessentertainmentgeneralhealthsciencesportstechnology. Note: you can't mix this param with the sources param.
sources
A comma-seperated string of identifiers for the news sources or blogs you want headlines from. Use the /top-headlines/sources endpoint to locate these programmatically or look at the sources index. Note: you can't mix this param with the country or category params.
q
Keywords or a phrase to search for.
pageSize
int
The number of results to return per page (request). 20 is the default, 100 is the maximum.
page
int
Use this to page through the results if the total results found is greater than the page size.
Response object
status
string
If the request was successful or not. Options: ok, error. In the case of error a code and message property will be populated.
totalResults
int
The total number of results available for your request.
articles
array[article]
The results of the request.
source
object
The identifier id and a display name name for the source this article came from.
author
string
The author of the article
title
string
The headline or title of the article.
description
string
A description or snippet from the article.
url
string
The direct URL to the article.
urlToImage
string
The URL to a relevant image for the article.
publishedAt
string
The date and time that the article was published, in UTC (+000)
content
string
The unformatted content of the article, where available. This is truncated to 200 chars.


** Sources /v2/top-headlines/sources **
This endpoint returns the subset of news publishers that top headlines (/v2/top-headlines) are available from. It's mainly a convenience endpoint that you can use to keep track of the publishers available on the API, and you can pipe it straight through to your users.

Request parameters
apiKey
required
Your API key. Alternatively you can provide this via the X-Api-Key HTTP header.

category
Find sources that display news of this category. Possible options: businessentertainmentgeneralhealthsciencesportstechnology. Default: all categories.

language
Find sources that display news in a specific language. Possible options: ardeenesfrheitnlnoptrusvudzh. Default: all languages.

country
Find sources that display news in a specific country. Possible options: aearataubebgbrcachcncocuczdeegfrgbgrhkhuidieilinitjpkrltlvmamxmyngnlnonzphplptrorsrusasesgsiskthtrtwuausveza. Default: all countries.

Response object
status
string
If the request was successful or not. Options: ok, error. In the case of error a code and message property will be populated.

sources
array[source]
The results of the request.

id
string
The identifier of the news source. You can use this with our other endpoints.

name
string
The name of the news source

description
string
A description of the news source

url
string
The URL of the homepage.

category
string
The type of news to expect from this news source.

language
string
The language that this news source writes in.

country
string
The country this news source is based in (and primarily writes about).


** Errors **
If you make a bad request we'll let you know by returning a relevant HTTP status code along with more details in the body.

Response object
status
string
If the request was successful or not. Options: ok, error. In the case of ok, the below two properties will not be present.

code
string
A short code identifying the type of error returned.

message
string
A fuller description of the error, usually including how to fix it.

HTTP status codes summary
200 - OK. The request was executed successfully.
400 - Bad Request. The request was unacceptable, often due to a missing or misconfigured parameter.
401 - Unauthorized. Your API key was missing from the request, or wasn't correct.
429 - Too Many Requests. You made too many requests within a window of time and have been rate limited. Back off for a while.
500 - Server Error. Something went wrong on our side.
Error codes
When an HTTP error is returned we populate the code and message properties in the response containing more information. Here are the possible options:

apiKeyDisabled - Your API key has been disabled.
apiKeyExhausted - Your API key has no more requests available.
apiKeyInvalid - Your API key hasn't been entered correctly. Double check it and try again.
apiKeyMissing - Your API key is missing from the request. Append it to the request with one of these methods.
parameterInvalid - You've included a parameter in your request which is currently not supported. Check the message property for more details.
parametersMissing - Required parameters are missing from the request and it cannot be completed. Check the message property for more details.
rateLimited - You have been rate limited. Back off for a while before trying the request again.
sourcesTooMany - You have requested too many sources in a single request. Try splitting the request into 2 smaller requests.
sourceDoesNotExist - You have requested a source which does not exist.
unexpectedError - This shouldn't happen, and if it does then it's our fault, not yours. Try the request again shortly.

Missing API key example
Definition
GET https://newsapi.org/v2/everything?q=bitcoin
Example response
{
"status": "error",
"code": "apiKeyMissing",
"message": "Your API key is missing. Append this to the URL with the apiKey param, or use the x-api-key HTTP header."
}


** Example Python usage **:
from newsapi import NewsApiClient

# Init
newsapi = NewsApiClient(api_key='API_KEY')

# /v2/top-headlines
top_headlines = newsapi.get_top_headlines(q='bitcoin',                                          
                                        sources='bbc-news,the-verge',
                                        category='business',
                                        language='en',
                                        country='us')

# /v2/everything
all_articles = newsapi.get_everything(q='bitcoin',
                                   sources='bbc-news,the-verge',
                                   domains='bbc.co.uk,techcrunch.com',                                             
                                   from_param='2017-12-01',
                                   to='2017-12-12',
                                   language='en',
                                   sort_by='relevancy',
                                   page=2)

# /v2/top-headlines/sources
sources = newsapi.get_sources()


** HTTPS Examples **:

Definition
GET https://newsapi.org/v2/everything?q=Apple&from=2026-04-09&sortBy=popularity&apiKey=API_KEY
Example request
import requests

url = ('https://newsapi.org/v2/everything?'
       'q=Apple&'
       'from=2026-04-09&'
       'sortBy=popularity&'
       'apiKey=API_KEY')

response = requests.get(url)

print r.json
Example response
{
"status": "ok",
"totalResults": 1102,
-"articles": [
-{
-"source": {
"id": "the-verge",
"name": "The Verge"
},
"author": "Tom Warren",
"title": "The MacBook Neo is the best thing to happen to Windows in years",
"description": "If there's one thing I know about Microsoft after covering the company for more than 20 years, it's that it will always respond to a competitive threat. Apple's MacBook Air convinced Microsoft and Intel to launch thin and light laptops with the Ultrabook init…",
"url": "https://www.theverge.com/tech/909140/microsoft-windows-11-fixes-macbook-neo-response-notepad",
"urlToImage": "https://platform.theverge.com/wp-content/uploads/sites/2/2026/03/268387_Apple_MacBook_Neo_AKrales_0507.jpg?quality=90&strip=all&crop=0%2C10.732984293194%2C100%2C78.534031413613&w=1200",
"publishedAt": "2026-04-09T13:02:21Z",
"content": "<ul><li></li><li></li><li></li></ul>\r\nMicrosoft always responds to a threat to Windows by improving the operating system.\r\nMicrosoft always responds to a threat to Windows by improving the operating … [+12999 chars]"
},
-{
-"source": {
"id": null,
"name": "Gizmodo.com"
},
"author": "James Whitbrook",
"title": "Go Titan Hunting in a Clip From This Week’s ‘Monarch: Legacy of Monsters’ (Exclusive)",
"description": "Titan X is ready to be found in a new look at the sophomore season of Apple TV's monster-filled series.",
"url": "https://gizmodo.com/monarch-legacy-of-monsters-season-2-episode-7-clip-titan-x-2000744489",
"urlToImage": "https://gizmodo.com/app/uploads/2026/04/monarch-season-2-episode-7-titan-x-preview-1200x675.jpg",
"publishedAt": "2026-04-09T15:00:40Z",
"content": "One of the big mysteries of this season of Monarch: Legacy of Monsters has been the mysterious, migratory beast known as Titan Xand brand-new kaiju for the show that has been causing mayhem around th… [+947 chars]"
}


Definition
GET https://newsapi.org/v2/top-headlines?country=us&apiKey=API_KEY
Example request
import requests
url = ('https://newsapi.org/v2/top-headlines?'
       'country=us&'
       'apiKey=API_KEY')
response = requests.get(url)
print response.json()
Example response
{
"status": "ok",
"totalResults": 37,
-"articles": [
-{
-"source": {
"id": "cbs-news",
"name": "CBS News"
},
"author": "Kathryn  Watson",
"title": "Independence Arch, or so-called \"Arc de Trump,\" plans include taxpayer funds - CBS News",
"description": "The president says the arch will commemorate the nation's 250th anniversary.",
"url": "https://www.cbsnews.com/news/arc-de-trump-taxpayer-funds/",
"urlToImage": "https://assets3.cbsnewsstatic.com/hub/i/r/2025/10/16/f706658c-b8c9-42d9-b0ce-7c01f192d149/thumbnail/1200x630/894ebd0aab6760c9e38d3ed3fa85976e/trumparch2.jpg",
"publishedAt": "2026-04-09T17:28:35Z",
"content": "Washington — American taxpayers will help fund the construction of President Trump's planned triumphal arch in Arlington, Virginia, according to the spending plan for the National Endowment for the H… [+1992 chars]"
}


Definition
GET https://newsapi.org/v2/top-headlines?sources=bbc-news&apiKey=API_KEY
Example request
import requests
url = ('https://newsapi.org/v2/top-headlines?'
       'sources=bbc-news&'
       'apiKey=API_KEY')
response = requests.get(url)
print response.json()
Example response
{
"status": "ok",
"totalResults": 10,
-"articles": [
-{
-"source": {
"id": "bbc-news",
"name": "BBC News"
},
"author": "BBC News",
"title": "'My daughter, 14, was groomed after meeting man on Roblox'",
"description": "The victim's mother was \"shocked, bewildered and angry\" after finding messages from Carlo Tritta.",
"url": "https://www.bbc.co.uk/news/articles/c78l92e9192o",
"urlToImage": "https://ichef.bbci.co.uk/ace/branded_news/1200/cpsprodpb/26b4/live/9e22eb10-325a-11f1-bdf9-bf5479a63eec.jpg",
"publishedAt": "2026-04-09T19:07:26.4097984Z",
"content": "\"I was just shocked, bewildered, really angry,\" she said.\r\n\"Not with my daughter because I had to keep saying to her 'I'm not angry with you' but I couldn't speak.\r\n\"I don't think your brain can take… [+1190 chars]"
}