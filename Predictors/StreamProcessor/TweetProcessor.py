# -*- coding: UTF-8 -*-
'''
Copyright (c) 2014, Yen-Lin Chen (hencrice@gmail.com)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''
from time import strftime, strptime
maxIdPrevBatch, maxIdCurrentBatch, idSet = 0, 0, set()

def process(tweet):
    '''
    This function will take a tweet in JSON format, produce a dictionary that can be inserted as a BSON record.
    '''
    twt={}
    # tweet['annotations'] = None
    # tweet['contributors'], tweet['favorited'], tweet['geo'], tweet['id'], tweet['in_reply_to_screen_name'], tweet['in_reply_to_status_id'], tweet['in_reply_to_status_id_str'], tweet['in_reply_to_user_id'], tweet['in_reply_to_user_id_str'], tweet['lang'], tweet['place'], tweet['retweeted'], tweet['truncated']
    twt['coordinates'] = tweet['coordinates'] # longitude, latitude
    twt['created_at'] = strftime('%Y-%m-%dT%H:%M:%S', strptime(tweet['created_at'], '%a %b %d %H:%M:%S +0000 %Y'))
    
    # beware that there's a new field "extended entities" (https://dev.twitter.com/docs/api/multiple-media-extended-entities)
    entities = twt['entities'] = {}
    rawJ = tweet['entities']
    entities['hashtags'] = rawJ['hashtags']
    if 'media' in rawJ:
        entities['media'] = [{'id_str': r['id_str'], 'media_url':r['media_url'], 'type':r['type'], 'size':{'h':r['sizes']['medium']['h'], 'w':r['sizes']['medium']['w']}, 'indices':r['indices']} for r in rawJ['media']]
    entities['urls'] = [{'url':r['url'], 'indices':r['indices']} for r in rawJ['urls']]
    entities['user_mentions'] = [{'id_str':r['id_str'], 'indices':r['indices'], 'screen_name':r['screen_name']} for r in rawJ['user_mentions']]
    entities['symbols'] = [{'text':r['text'], 'indices':r['indices']} for r in rawJ['symbols']]

    twt['filter_level'] = tweet['filter_level']
    twt['favorite_count'] = tweet['favorite_count']
    twt['id_str'] = tweet['id_str']
    twt['in_reply_to_screen_name'] = tweet['in_reply_to_screen_name']
    twt['in_reply_to_status_id_str'] = tweet['in_reply_to_status_id_str']
    twt['in_reply_to_user_id_str'] = tweet['in_reply_to_user_id_str']
    # might add code for the "place" field later
    if 'possibly_sensitive' in tweet:
        twt['coordinates'] = tweet['possibly_sensitive']
    twt['retweet_count'] = tweet['retweet_count']
    
    txt = tweet['text']
    if 'retweeted_status' in tweet:
        rawJ = tweet['retweeted_status']
        twt['retweeted_status'] = {'favorite_count': rawJ['retweet_count'], "retweet_count": rawJ['retweet_count'], 'text': rawJ['text']}
        txt += ' ' + rawJ['text']
    
    if 'scopes' in tweet:
        twt['scopes'] = tweet['scopes']
    twt['source'] = tweet['source']
    twt['text'] = tweet['text']

    user = twt['user'] = {}
    rawJ = tweet['user']
    user['created_at'] = strftime('%Y-%m-%dT%H:%M:%S', strptime(rawJ['created_at'], '%a %b %d %H:%M:%S +0000 %Y'))
    user['default_profile'] = rawJ['default_profile']
    user['default_profile_image'] = rawJ['default_profile_image']
    user['description'] = rawJ['description']
    if 'entities' in rawJ:
        user['entities'] = {'urls':[{'url':r['url'], 'indices':r['indices']} for r in rawJ['entities']['url']['urls']],
                            'description':[{'url':r['url'], 'indices':r['indices']} for r in rawJ['entities']['description']['urls']]}
    user['favourites_count'] = rawJ['favourites_count']
    user['followers_count'] = rawJ['followers_count']
    user['friends_count'] = rawJ['friends_count']
    user['id_str'] = rawJ['id_str']
    user['lang'] = rawJ['lang']
    user['listed_count'] = rawJ['listed_count']
    user['statuses_count'] = rawJ['statuses_count']
    user['verified'] = rawJ['verified']
    return twt, txt

def filter(tweet, config={'lang':'en'}):
    global maxIdPrevBatch, idSet, maxIdCurrentBatch # global within this module
    if 'created_at' in tweet and tweet['lang'] == config['lang'] and tweet['id'] not in idSet and tweet['id'] > maxIdPrevBatch:  # Non-duplicated English tweet
        # to prevent duplicated tweets
        idSet.add(tweet['id'])
        if tweet['id'] > maxIdCurrentBatch:
            maxIdCurrentBatch = tweet['id']
        return True
    return False