'''
Copyright (c) 2014, Yen-Lin Chen (hencrice@gmail.com)
All rights reserved.
'''
# -*- coding: UTF-8 -*-
import json
from time import strftime, strptime
from cPickle import load
import os
import argparse
from itertools import izip
from numpy import array, argmax, amax
from TwitterStream import getTwitterStream
from SocketAdapter import connectSocketAdapter, saveTweetsInDB # This module can be downloaded from AsterixUtility repo

def predictOnStream(predictionModelsPath, bufferSize=1000, streamSrc=getTwitterStream, streamSrcConfig=[]):
    predictors = sorted([fName for fName in next(os.walk(predictionModelsPath))[2] if fName.endswith('.pkl') and fName[0] == 'c'])
    tfIdfVectorizers = sorted([fName for fName in next(os.walk(predictionModelsPath))[2] if fName.endswith('.pkl') and fName[0] == 'v'])
    predictors = [load(open(predictionModelsPath + pName, 'rb')) for pName in predictors]
    tfIdfVectorizers = [load(open(predictionModelsPath + vName, 'rb')) for vName in tfIdfVectorizers]
    vecAndPredTuple = tuple(vecAndPred for vecAndPred in izip(tfIdfVectorizers, predictors))

    sock=connectSocketAdapter()
    with streamSrc(streamSrcConfig) as stream:
        print('Stream established.')
        idSet = set()
        maxIdPrevBatch, maxIdCurrentBatch = 0, 0
        processedTweetBuff = []
        rawDataArr = []
        userFieldsToKeep = ('created_at', 'default_profile', 'default_profile_image', 'description', 'favourites_count', 'followers_count', 'friends_count', 'id_str', 'lang', 'listed_count', 'statuses_count', 'verified')  # 'entities' is optional, but when it does appear, it's preserved
        for t in stream:
            try:
                tweet = json.loads(t)
            except ValueError:  # Might be caused by https://dev.twitter.com/docs/streaming-apis/connecting#Stalls
                continue
            if 'created_at' in tweet and tweet['lang'] == 'en' and tweet['id'] not in idSet and tweet['id'] > maxIdPrevBatch:  # Non-duplicated English tweet
                # to prevent duplicated tweets
                idSet.add(tweet['id']);
                maxIdCurrentBatch=tweet['id'] if tweet['id']>maxIdCurrentBatch else maxIdCurrentBatch

                tweet['annotations'] = None
                # delete all redundant fields and nested fields. Also transform some array of json into list of tuples
                if 'filter_level' in tweet:
                    del tweet['filter_level']
                del tweet['contributors'], tweet['favorited'], tweet['geo'], tweet['id'], tweet['in_reply_to_screen_name'], tweet['in_reply_to_status_id'], tweet['in_reply_to_status_id_str'], tweet['in_reply_to_user_id'], tweet['in_reply_to_user_id_str'], tweet['lang'], tweet['place'], tweet['retweeted'], tweet['truncated']
                tweet['coordinates'] = None if tweet['coordinates'] is None else tuple(tweet['coordinates']['coordinates'])  # (longitude, latitude)
                tweet['created_at'] = strftime('%Y-%m-%dT%H:%M:%S', strptime(tweet['created_at'], '%a %b %d %H:%M:%S +0000 %Y'))
                tweet.pop('current_user_retweet', None)  # this field might not exist

                entities = tweet['entities']
                entities['media'] = []
                # entities['hashtags'] = [{'text':h['text'], 'indices':h['indices']} for h in entities['hashtags']]
                if 'media' in entities:
                    entities['media'] = [{'id_str': m['id_str'], 'media_url':m['media_url'], 'type':m['type'], 'sizes':[m['sizes']['medium']['h'], m['sizes']['medium']['w']], 'indices':m['indices']} for m in entities['media']]
                entities['urls'] = [{'url':u['url'], 'indices':u['indices']} for u in entities['urls']]
                entities['user_mentions'] = [{'id_str':u['id_str'], 'indices':u['indices']} for u in entities['user_mentions']]
                entities['symbols'] = [{'text':s['text'], 'indices':s['indices']} for s in entities['symbols']]

                if 'possibly_sensitive' in tweet:
                    del tweet['possibly_sensitive']
		if 'quoted_status_id' in tweet:
                    del tweet['quoted_status_id']
                if 'quoted_status_id_str' in tweet:
                    del tweet['quoted_status_id_str']    
                if 'retweeted_status' in tweet:
                    rawDataArr.append(tweet['text'] + ' ' + tweet['retweeted_status']['text'])
                    del tweet['retweeted_status']
                else:
                    rawDataArr.append(tweet['text'])
                if 'scopes' in tweet:
                    del tweet['scopes']

                userEntities = None
                if 'entities' in tweet['user']:
                    userEntities = {'urls':[{'url':u['url'], 'indices':u['indices']} for u in tweet['user']['entities']['url']['urls']],
                                             'description':[{'url':u['url'], 'indices':u['indices']} for u in tweet['user']['entities']['description']['urls']]}
                tweet['user'] = {fieldName:tweet['user'][fieldName] for fieldName in userFieldsToKeep}
                tweet['user']['entities'] = userEntities
                tweet['user']['created_at'] = strftime('%Y-%m-%dT%H:%M:%S', strptime(tweet['user']['created_at'], '%a %b %d %H:%M:%S +0000 %Y'))
                processedTweetBuff.append(tweet)
            if len(processedTweetBuff) > bufferSize:
                # append semantic scores
                resultsProba = map(lambda vecAndPred: vecAndPred[1].predict_proba(vecAndPred[0].transform(array(rawDataArr))), vecAndPredTuple)
                starRankings = (argmax(resultsProba, 2) + 1.0).T.tolist()
                probabilities = amax(resultsProba, 2).T.tolist()
                for tweet, starR, proba in izip(processedTweetBuff, starRankings, probabilities):
                    tweet['semantic_scores'] = starR
                    tweet['semantic_probabilities'] = proba
                saveTweetsInDB(processedTweetBuff, sock)
                processedTweetBuff[:] = []  # empty the buffer
                idSet.clear()
                maxIdPrevBatch = maxIdCurrentBatch

    sock.close()
    print('Connection with SocketAdapter is closed.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process Twitter Stream. Assign semantic scores and the corresponding probabilities to each tweet by multiple predictors.')
    parser.add_argument('-b', '--bufferSize', type=int, default=1000, help='The number of tweets to buffer before writing to datafeed.')
    parser.add_argument('-mp', '--modelsPath', required=True, help='The path to the folder that contains the trained predictors.')
    args = parser.parse_args()
    predictOnStream(args.modelsPath, args.bufferSize)  # in our server, this should be './models/' because all the models should be put there

# How to set up datafeed and this module to start ingesting Tweets stream:
# I tested this on the newer version of Asterix binary provided by Morris in the New Version AsterixDB folder
# in the AsterixUtility repo.

# 1. In Asterix's web interface, copy and run the aql statements in TweetDataType.aql in dataTypes folder in the AsterixUtility repo.
# This will create the datatype for tweets, initiate a datafeed and the corresponding SocketAdapter which listens on a local socket.

# 2. Download Morris' SocketAdapter module from AsterixUtility repo, put it in this folder.

# 3. Also check whether you have downloaded the trained Machine Learning models in "./model/" folder. If not, followed the instructions
# there.

# 4. Use Enthought Canopy's Python binary (on my machine, its path is: /home/hencrice/AdditionalPrograms/Canopy_64bit/User/bin/python) instead of your system
# Python interpreter to execute this program. For example: $ PathToPythonBin/python SemanticPredictor.py -mp ./models/
# You can also check the meaning of command line argument by running $ PathToPythonBin/python SemanticPredictor.py -h

# 5. Use these AQL statements to check whether the data is increasing:
# use dataverse feeds;
# count(for $l in dataset('TweetsDataSet') return $l);


# The following information is not relevant to the steps above. They are env variables in my .bashrc for Asterix
# export JAVA_HOME=/usr/lib/jvm/java-1.7.0-openjdk-amd64
# export MANAGIX_HOME=/home/hencrice/AdditionalPrograms/asterix-installer-0.8.6-SNAPSHOT-binary-assembly
# export PATH=$PATH:$MANAGIX_HOME/bin
