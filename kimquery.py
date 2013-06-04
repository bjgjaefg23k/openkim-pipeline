import urllib 
import urllib2 
import simplejson
import itertools
from config import PipelineQueryError

def query(querydata, queryrules="", keys=None):
    # set up the globals for how to interact with the website
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
    arr = simplejson.loads(answer)
    if keys:
        result = [ { k:v for k,v in itertools.izip(keys, elem) } for elem in arr ]
        return result 
    return arr