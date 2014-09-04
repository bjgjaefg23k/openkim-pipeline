import urllib
import urllib2
import itertools
from config import PipelineQueryError
import json
import os

def prepare_dns():
    resolv = "/etc/resolv.conf"
    dnsline = "nameserver 127.0.0.1"
    if not open(resolv).read().startswith(dnsline):
        os.system("sudo sed -i '1i"+dnsline+"' "+resolv)

def query_datomic(querydata, queryrules="", keys=None):
    # set up the globals for how to interact with the website
    prepare_dns()

    url = 'http://openkim.org:3000/api/query'
    user_agent = "OpenKIM Pipeline (http://pipeline.openkim.org/)"
    header = {'User-Agent' : user_agent, "Content-type": "application/x-www-form-urlencoded"}

    # build our actual query
    values = {"querydata": querydata}
    if queryrules:
        values["queryrules"] = queryrules

    # encode, send, and read the response
    data = urllib.urlencode(values)
    request  = urllib2.Request(url, data, header)
    response = urllib2.urlopen(request)
    answer = response.read()
    response.close()

    if not answer:
        raise PipelineQueryError("No response")

    # we got back JSON, let's convert and apply labels if requested
    arr = json.loads(answer)
    if keys:
        result = [ { k:v for k,v in itertools.izip(keys, elem) } for elem in arr ]
        return result
    return arr

def query_mongo(query, url="", decode=False):
    # set up the globals for how to interact with the website
    prepare_dns()

    url = url or 'https://query.openkim.org/api'
    user_agent = "OpenKIM Pipeline (http://pipeline.openkim.org/)"
    header = {'User-Agent' : user_agent, "Content-type": "application/x-www-form-urlencoded"}
    data = urllib.urlencode(dict((key,json.dumps(val)) for (key,val) in query.iteritems()))
    request  = urllib2.Request(url, data, header)
    response = urllib2.urlopen(request)
    answer = response.read()
    response.close()

    if not answer:
        raise PipelineQueryError("No response")

    # we got back JSON, let's check if we got errors back
    check = json.loads(answer)
    if isinstance(check, dict) and check.get('error'):
        raise PipelineQueryError("Error received: %r" % check['error'])

    if decode:
        return json.loads(answer)
    return answer

def query_property_validator(filename, url=""):
    prepare_dns()

    url = url or "http://query.openkim.org:5005/"
    user_agent = "OpenKIM Pipeline (http://pipeline.openkim.org/)"
    header = {'User-Agent' : user_agent, "Content-type": "application/x-www-form-urlencoded"}
    #data = urllib.urlencode(open(filename).read())
    data = open(filename).read()
    request  = urllib2.Request(url, data, header)
    response = urllib2.urlopen(request)
    answer = response.read()
    response.close()

    if not answer:
        raise PipelineQueryError("No response")

    return answer

query = query_mongo
