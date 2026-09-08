"""One-shot, robots-aware news-source connectivity check; never publishes article bodies."""
import concurrent.futures, datetime, html, json, os, re, time
import urllib.request, urllib.error, urllib.parse, urllib.robotparser
from html.parser import HTMLParser
UA = "SBE-News-Source-Check/1.0 (+https://github.com/j-hwan9/SBE-US-Market-Dashboard)"
SOURCES = [
("BR&R RSS","https://biosimilarsrr.com/feed/"),
("Drug Channels RSS","https://www.drugchannels.net/feeds/posts/default?alt=rss"),
("Pharmaceutical Executive date check","https://www.pharmexec.com/view/fda-approves-ennumo-decrease-incidence-infection-febrile-neutropenia"),
]
class Page(HTMLParser):
 def __init__(self):
  super().__init__();self.meta={};self.feeds=[];self.scripts=[];self.active=False;self.buf=[];self.title=[];self.intitle=False
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=="meta":self.meta[a.get("property",a.get("name","")).lower()]=a.get("content","")
  if tag=="link" and a.get("type") in ("application/rss+xml","application/atom+xml"):self.feeds.append(a.get("href"))
  if tag=="script" and a.get("type")=="application/ld+json":self.active=True;self.buf=[]
  if tag=="title":self.intitle=True
 def handle_data(self,s):
  if self.active:self.buf.append(s)
  if self.intitle:self.title.append(s)
 def handle_endtag(self,tag):
  if tag=="script" and self.active:
   self.active=False
   try:self.scripts.append(json.loads("".join(self.buf)))
   except ValueError:pass
  if tag=="title":self.intitle=False
def fetch(url):
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":UA}),timeout=25) as r:
   return r.status,r.read(4000000).decode("utf-8","replace"),r.headers.get("Content-Type","")
 except urllib.error.HTTPError as e:return e.code,"",""
def nodes(v):
 if isinstance(v,dict):
  yield v
  for x in v.values():yield from nodes(x)
 elif isinstance(v,list):
  for x in v:yield from nodes(x)
def check(item):
 name,url=item;r={"source":name,"sample_url":url}
 try:
  origin=urllib.parse.urlsplit(url);roboturl=origin.scheme+"://"+origin.netloc+"/robots.txt"
  status,body,typ=fetch(roboturl);r["robots_status"]=status
  if status==200 and "<html" not in body.lower():
   rp=urllib.robotparser.RobotFileParser();rp.parse(body.splitlines())
   r["robots_allowed"]=rp.can_fetch(UA,url)
   r["robots_rules"]=body[:18000]
   if not r["robots_allowed"]:r["result"]="robots_disallowed";return r
   delay=rp.crawl_delay(UA) or 1
   if delay>30:r["result"]="crawl_delay_requires_separate_run";return r
   time.sleep(delay)
  elif status in (404,410):r["robots_allowed"]=True
  else:r["result"]="robots_unverified";return r
  status,body,typ=fetch(url);r["http_status"]=status;r["content_type"]=typ
  if status!=200:r["result"]="http_blocked_or_missing";return r
  if "xml" in typ or body.lstrip().startswith("<?xml"):
   import xml.etree.ElementTree as ET
   root=ET.fromstring(body);items=root.findall(".//item")
   r["items"]=[{"title":i.findtext("title"),"published":i.findtext("pubDate"),"url":i.findtext("link")} for i in items[:12]]
   r["result"]="rss_metadata_ok" if items and all(x["title"] and x["published"] and x["url"] for x in r["items"]) else "feed_parser_needed"
   return r
  p=Page();p.feed(body);r["date_metadata"]={k:v for k,v in p.meta.items() if any(s in k for s in ("date","time","publish"))}
  r["structured_dates"]=[{k:v for k,v in n.items() if k in ("@type","datePublished","dateModified","headline")} for n in nodes(p.scripts) if n.get("datePublished")]
  r["time_elements"]=re.findall(r"<time[^>]*>.*?</time>",body,re.I|re.S)[:6]
  r["title"]=p.meta.get("og:title") or "".join(p.title).strip()
  r["published_date"]=p.meta.get("article:published_time") or p.meta.get("date") or p.meta.get("dc.date.issued")
  for n in nodes(p.scripts):
   if n.get("datePublished") and not r["published_date"]:r["published_date"]=n["datePublished"]
  r["rss_links"]=p.feeds
  # A connectivity signal only: production matching must isolate editorial body from navigation.
  r["biosimilar_text_present"]=bool(re.search(r"biosimilar",body,re.I))
  r["result"]="metadata_ok" if r["title"] and r["published_date"] and r["biosimilar_text_present"] else "parser_or_article_discovery_needed"
 except Exception as e:r["result"]="network_error";r["error"]=str(e)
 return r
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(check,SOURCES))
report={"checked_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"user_agent":UA,"scope":"One sample per publisher; technical access, not reuse permission or reliability guarantee.","results":results}
os.makedirs("reports",exist_ok=True)
with open("reports/news-source-check.json","w") as f:json.dump(report,f,ensure_ascii=False,indent=2)
print(json.dumps(report,ensure_ascii=False))
summary="| Source | Result | HTTP | Title | Published |\n|---|---|---|---|---|\n"
for r in results:summary+="| "+ " | ".join(str(r.get(k,"")) .replace("|","/") for k in ("source","result","http_status","title","published_date"))+" |\n"
if os.environ.get("GITHUB_STEP_SUMMARY"):
 with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write(summary)
