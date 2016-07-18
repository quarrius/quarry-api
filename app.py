#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import base64
import hmac
import hashlib
import json
import datetime
import os.path

import boto3
import chalice

app = chalice.Chalice(app_name='quarry-api')
app.debug = True

ddb = boto3.resource('dynamodb')
s3c = boto3.client('s3')

KEY_EXPIRES_IN      = datetime.timedelta(hours=4)
MIN_UPLOAD_SIZE     = 0
MAX_UPLOAD_SIZE     = 16 * 1024 * 1024

@app.route('/')
def index():
    return {'hello': 'world'}

@app.route('/maps/{map_id}')
def map_get(map_id):

    tbl = ddb.Table('quarry-maps')
    try:
        map_data = tbl.get_item(Key={'id': map_id})['Item']
    except KeyError as err:
        raise chalice.NotFoundError('No map found for id: {}'.format(map_id))

    return map_data

@app.route('/upload/authorize/{api_key}')
def upload_credentials_get(api_key):
    # req_data = app.json_body
    worlds_tbl = ddb.Table('quarry-worlds')
    world = worlds_tbl.get_item(Key={'api_key': api_key})['Item']

    user_id = world['owner_id']
    world_id = world['id']

    return s3c.generate_presigned_post(
        Bucket='quarry-worlds',
        Key=os.path.join('uploads', user_id, world_id, '${filename}'),
        Fields={
            'acl':                          'private',
            'success_action_status':        200,
            'x-amz-meta-quarry-api-key':    api_key,
            'x-amz-meta-quarry-user-id':    user_id,
            'x-amz-meta-quarry-world-id':   world_id,
        },
        Conditions=[
            {'acl':                         'private'},
            ['content-length-range',        MIN_UPLOAD_SIZE, MAX_UPLOAD_SIZE],
            {'x-amz-meta-quarry-api-key':   api_key},
            {'x-amz-meta-quarry-user-id':   user_id},
            {'x-amz-meta-quarry-world-id':  world_id},

        ],
        ExpiresIn=KEY_EXPIRES_IN.seconds,
    )
