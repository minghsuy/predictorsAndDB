# -*- coding: UTF-8 -*-
'''
Copyright (c) 2014, Yen-Lin Chen (hencrice@gmail.com)
All rights reserved.
'''
import json
from cPickle import load
import os
import argparse
from itertools import izip
from numpy import array, argmax, amax
from TwitterStream import getTwitterStream
from StreamProcessor import TweetProcessor
from pymongo import MongoClient

def predictOnStream(predictionModelsPath, bufferSize=1000, streamSrc=getTwitterStream, streamSrcConfig={}, streamProcessor=TweetProcessor):
    '''
    All classes of streamProcessor need to implement the function, process(), as the common interface.
    '''
    predictors = sorted([fName for fName in next(os.walk(predictionModelsPath))[2] if fName.endswith('.pkl') and fName[0] == 'c'])
    tfIdfVectorizers = sorted([fName for fName in next(os.walk(predictionModelsPath))[2] if fName.endswith('.pkl') and fName[0] == 'v'])
    predictors = [load(open(predictionModelsPath + pName, 'rb')) for pName in predictors]
    tfIdfVectorizers = [load(open(predictionModelsPath + vName, 'rb')) for vName in tfIdfVectorizers]
    vecAndPredTuple = tuple(vecAndPred for vecAndPred in izip(tfIdfVectorizers, predictors))
    db=MongoClient('ds045089.mongolab.com', 45089)['tanav']
    db.authenticate('user', 'password')
    tweetsColl=db.tweets

    with streamSrc(streamSrcConfig) as stream:
        print('Stream established.')
        idSet = set()
        maxIdPrevBatch, maxIdCurrentBatch = 0, 0
        processedTweetBuff = []
        rawTxtArr = []
        
        for t in stream:
            try:
                t = json.loads(t)
            except ValueError:  # Might be caused by the keep-alive new line character described in https://dev.twitter.com/docs/streaming-apis/connecting#Stalls
                continue
            if streamProcessor.filter(t):
                processedT, rawTxt = streamProcessor.process(t)
                rawTxtArr.append(rawTxt)
                processedTweetBuff.append(processedT)
                if len(processedTweetBuff) > bufferSize:
                    # append semantic scores
                    resultsProba = map(lambda vecAndPred: vecAndPred[1].predict_proba(vecAndPred[0].transform(array(rawTxtArr))), vecAndPredTuple)
                    starRankings = (argmax(resultsProba, 2) + 1.0).T.tolist()
                    probabilities = amax(resultsProba, 2).T.tolist()
                    for tweet, starR, proba in izip(processedTweetBuff, starRankings, probabilities):
                        tweet['semantic_scores'] = starR
                        tweet['semantic_probabilities'] = proba
                    tweetsColl.insert(processedTweetBuff) # bulk insert into MongoDB
                    processedTweetBuff[:] = []  # empty the buffer
                    rawTxtArr[:] = []
                    streamProcessor.idSet.clear()
                    streamProcessor.maxIdPrevBatch = streamProcessor.maxIdCurrentBatch

    print('Stream terminated')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process Twitter Stream. Assign semantic scores and the corresponding probabilities to each tweet by multiple predictors.')
    parser.add_argument('-b', '--bufferSize', type=int, default=1000, help='The number of tweets to buffer before writing to datafeed.')
    parser.add_argument('-mp', '--modelsPath', required=True, help='The path to the folder that contains the trained predictors.')
    args = parser.parse_args()
    predictOnStream(args.modelsPath, args.bufferSize)  # in our server, this should be './models/' because all the models should be put there