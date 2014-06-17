# -*- coding: UTF-8 -*-
'''
Copyright (c) 2014, Yen-Lin Chen (hencrice@gmail.com)
'''
import oauth2
import sys
import urllib2
from contextlib import contextmanager

# See Assignment 1 instructions or README for how to get these credentials
access_token_key = "ApplyAndGetOneYourself"
access_token_secret = "ApplyAndGetOneYourself"
 
consumer_key = "ApplyAndGetOneYourself"
consumer_secret = "ApplyAndGetOneYourself"

oauth_token = oauth2.Token(key=access_token_key, secret=access_token_secret)
oauth_consumer = oauth2.Consumer(key=consumer_key, secret=consumer_secret)

# Construct, sign, and open a twitter request using the hard-coded credentials above.
@contextmanager
def getTwitterStream(requestParam, url='https://stream.twitter.com/{0}/statuses/sample.json', apiVer=1.1, debugLv=0):
    # Construction the request but has not yet sent it out.
    req = oauth2.Request.from_consumer_and_token(oauth_consumer, token=oauth_token, http_method='GET', http_url=url.format(apiVer), parameters=requestParam)

    # Sign the request.
    req.sign_request(oauth2.SignatureMethod_HMAC_SHA1(), oauth_consumer, oauth_token)
    # headers = req.to_header()  # seems useless 
    
    # each handler knows how to open URLs for a particular URL scheme (http, ftp, etc.)
    http_handler = urllib2.HTTPHandler(debuglevel=debugLv)
    https_handler = urllib2.HTTPSHandler(debuglevel=debugLv)
    # when you fetch a URL you use an opener
    opener = urllib2.OpenerDirector()
    opener.add_handler(http_handler)
    opener.add_handler(https_handler)
    url = req.to_url()  # this must be preserved because it 'serialize a URL for a GET request
    stream = opener.open(url)
    try:
        yield stream
    except KeyboardInterrupt:
        stream.close()
        print('Twitter Stream closed.')
    # except Exception: # possible to implement backoff reconnecting here?
    #     pass

if __name__ == '__main__':
    parameters = []
    with getTwitterStream(parameters) as stream:
        for i, tweet in enumerate(stream):
            print(tweet.strip())
            if i > 10:
                sys.exit()
