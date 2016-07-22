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

KEY_EXPIRES_IN      = datetime.timedelta(hours=1)
MIN_UPLOAD_SIZE     = 0
MAX_UPLOAD_SIZE     = 16 * 1024 * 1024
UPLOAD_BUCKET       = 'quarrius-input'

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
            {'acl':                             'private'},
            ['content-length-range',            MIN_UPLOAD_SIZE, MAX_UPLOAD_SIZE],
            {'x-amz-meta-quarry-api-key':   post_api_key},
            {'x-amz-meta-quarry-user-id':   post_user_guid},
            {'x-amz-meta-quarry-world-id':  post_world_guid},

        ],
        ExpiresIn=KEY_EXPIRES_IN.seconds,
    )

@app.route('/authorize-upload/world-archive/<uuid:api_key>')
@json_response
def get_archive_upload_credentials(api_key):
    # world = get_object_or_404(World, World.api_key == api_key)
    world = World.select().where(World.api_key == api_key).first()
    user = world.user

    post_api_key = str(api_key)
    post_user_guid = str(user.guid)
    post_world_guid = str(world.guid)
    return s3c.generate_presigned_post(
        Bucket=UPLOAD_BUCKET,
        Key='world-archives/{archive_name}.zip'.format(archive_name=post_api_key),
        Fields={
            'acl':                          'private',
            'success_action_status':        200,
            'x-amz-meta-quarry-api-key':    post_api_key,
            'x-amz-meta-quarry-user-id':    post_user_guid,
            'x-amz-meta-quarry-world-id':   post_world_guid,
        },
        Conditions=[
            {'acl':                         'private'},
            ['content-length-range',        MIN_UPLOAD_SIZE, MAX_UPLOAD_SIZE],
            {'x-amz-meta-quarry-api-key':   post_api_key},
            {'x-amz-meta-quarry-user-id':   post_user_guid},
            {'x-amz-meta-quarry-world-id':  post_world_guid},

        ],
        ExpiresIn=KEY_EXPIRES_IN.seconds,
    )

if __name__ == '__main__':
    app.config['DEBUG'] = True
    app.config['TESTING'] = True
    app.run()
