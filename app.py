#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import json
import datetime
import os.path
import functools

import flask
import boto3
from playhouse.flask_utils import FlaskDB, get_object_or_404

from toybox.config import CFG
from toybox.models import World, User
from toybox.db import DATABASE

app = flask.Flask(__name__)
flask_db = FlaskDB(app, DATABASE)

s3c = boto3.client('s3')

UPLOAD_KEY_TTL, \
UPLOAD_BUCKET       = CFG.mget([
    'config:quarry-api:UPLOAD_KEY_TTL',
    'config:quarry-api:UPLOAD_BUCKET',
])
UPLOAD_KEY_TTL = int(UPLOAD_KEY_TTL)

def json_response(orig_func):
    @functools.wraps(orig_func)
    def actual_func(*args, **kwargs):
        return flask.jsonify(**orig_func(*args, **kwargs))
    return actual_func

@app.route('/')
@json_response
def index():
    return {'hello': 'world'}

@app.route('/maps/<string:map_token>')
@json_response
def map_get(map_token):
    world = get_object_or_404(World, World.map_token == map_token)

    return world.xattr['map_config']

@app.route('/authorize-upload/world/<uuid:api_key>')
@json_response
def get_stream_upload_credentials(api_key):
    world = get_object_or_404(World, World.api_key == api_key)
    user = world.user

    post_api_key = str(api_key)
    post_user_guid = str(user.guid)
    post_world_guid = str(world.guid)
    size_range = [int(s) for s in CFG.mget([
        'config:quarry-api:WORLD_OBJ_MIN_SIZE',
        'config:quarry-api:WORLD_OBJ_MAX_SIZE',
    ])]
    return s3c.generate_presigned_post(
        Bucket=UPLOAD_BUCKET,
        Key=os.path.join('worlds', post_user_guid, post_world_guid, '${filename}'),
        Fields={
            'acl':                              'private',
            'success_action_status':            200,
            'x-amz-meta-quarry-api-key':    post_api_key,
            'x-amz-meta-quarry-user-id':    post_user_guid,
            'x-amz-meta-quarry-world-id':   post_world_guid,
        },
        Conditions=[
            {'acl':                         'private'},
            ['content-length-range'] +      size_range,
            {'x-amz-meta-quarry-api-key':   post_api_key},
            {'x-amz-meta-quarry-user-id':   post_user_guid},
            {'x-amz-meta-quarry-world-id':  post_world_guid},

        ],
        ExpiresIn=UPLOAD_KEY_TTL,
    )

@app.route('/authorize-upload/world-archive/<uuid:api_key>')
@json_response
def get_archive_upload_credentials(api_key):
    world = get_object_or_404(World, World.api_key == api_key)
    user = world.user

    post_api_key = str(api_key)
    post_user_guid = str(user.guid)
    post_world_guid = str(world.guid)
    size_range = [int(s) for s in CFG.mget([
        'config:quarry-api:ARCHIVE_MIN_SIZE',
        'config:quarry-api:ARCHIVE_MAX_SIZE',
    ])]
    return s3c.generate_presigned_post(
        Bucket=UPLOAD_BUCKET,
        Key='world-archives/{archive_name}.zip'.format(archive_name=post_api_key),
        Fields={
            'acl':                          'private',
            # 'success_action_status':        200,
            'x-amz-meta-quarry-api-key':    post_api_key,
            'x-amz-meta-quarry-user-id':    post_user_guid,
            'x-amz-meta-quarry-world-id':   post_world_guid,
        },
        Conditions=[
            {'acl':                         'private'},
            ['content-length-range'] +      size_range,
            {'x-amz-meta-quarry-api-key':   post_api_key},
            {'x-amz-meta-quarry-user-id':   post_user_guid},
            {'x-amz-meta-quarry-world-id':  post_world_guid},

        ],
        ExpiresIn=UPLOAD_KEY_TTL,
    )

if __name__ == '__main__':
    app.config['DEBUG'] = True
    app.config['TESTING'] = True
    app.run()
