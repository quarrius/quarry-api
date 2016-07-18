#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import json
import datetime
import os.path

import boto3
import chalice

from toybox import DB_INIT, World, User

app = chalice.Chalice(app_name='quarry-api')
app.debug = True

ddb = boto3.resource('dynamodb')
s3c = boto3.client('s3')

DB_OBJ = DB_INIT('')

KEY_EXPIRES_IN      = datetime.timedelta(hours=1)
MIN_UPLOAD_SIZE     = 0
MAX_UPLOAD_SIZE     = 16 * 1024 * 1024
UPLOAD_BUCKET       = 'quarrius-input'

@app.route('/')
def index():
    return {'hello': 'world'}

@app.route('/maps/{map_id}')
def map_get(map_id):
    world = World.select().where(World.map_token == map_id).first()
    if world is None:
        raise chalice.NotFoundError('No map found for id: {}'.format(map_id))
    else:
        # return world data
        return {}
    tbl = ddb.Table('quarry-maps')
    try:
        map_data = tbl.get_item(Key={'id': map_id})['Item']
    except KeyError as err:
        raise chalice.NotFoundError('No map found for id: {}'.format(map_id))

    return map_data

@app.route('/authorize-upload/world/{api_key}')
def get_stream_upload_credentials(api_key):
    world = World.select().where(World.api_key == api_key).first()
    if world is None:
        # TODO: change to 403 forbidden
        raise chalice.NotFoundError('bad api_key')
    else:
        user = world.user
        return s3c.generate_presigned_post(
            Bucket=UPLOAD_BUCKET,
            Key=os.path.join('worlds', user.guid, world.guid, '${filename}'),
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

@app.route('/authorize-upload/world-archive/{api_key}')
def get_archive_upload_credentials(api_key):
    world = World.select().where(World.api_key == api_key).first()
    if world is None:
        # TODO: change to 403 forbidden
        raise chalice.NotFoundError('bad api_key')
    else:
        user = world.user
        return s3c.generate_presigned_post(
            Bucket=UPLOAD_BUCKET,
            Key='world-archives/{world_guid}.zip'.format(world_guid=world.guid),
            Fields={
                'acl':                          'private',
                'success_action_status':        200,
                'x-amz-meta-quarry-api-key':    api_key,
                'x-amz-meta-quarry-user-id':    user.guid,
                'x-amz-meta-quarry-world-id':   world.guid,
            },
            Conditions=[
                {'acl':                         'private'},
                ['content-length-range',        MIN_UPLOAD_SIZE, MAX_UPLOAD_SIZE],
                {'x-amz-meta-quarry-api-key':   api_key},
                {'x-amz-meta-quarry-user-id':   user.guid},
                {'x-amz-meta-quarry-world-id':  world.guid},

            ],
            ExpiresIn=KEY_EXPIRES_IN.seconds,
        )
