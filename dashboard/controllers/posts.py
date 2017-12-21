from datetime import datetime
from bottle import get, post, default_app
from elasticsearch import Elasticsearch

from dashboard.auth import get_user_or_401
from dashboard.models import (BasketArticleList, PoolArticle, Authors, PostTypeEnum,
                              PostStatusEnum, ShowStatusEnum, JudgeStatusEnum)
from dashboard.db import db
from dashboard.serializers import basket_article_list_serializer
from dashboard.plugins import page_plugin
from dashboard.utils import plain_forms, short_uuid, get_text_from_tag
from dashboard.validators import create_post_validator


@get('/v1/posts/set_top/<post_id>')
def set_top(post_id):
    get_user_or_401()
    post_ = BasketArticleList.get(BasketArticleList.post_id == post_id)

    with db.atomic():
        post_.is_top = False
        post_.save()

    return {}


@get('/v1/posts/unset_top/<post_id>')
def unset_top(post_id):
    get_user_or_401()
    post_ = BasketArticleList.get(BasketArticleList.post_id == post_id)

    with db.atomic():
        post_.is_top = True
        post_.save()

    return {}


@get('/v1/posts', apply=[page_plugin])
def get_posts():
    # get_user_or_401()
    posts = BasketArticleList.select()
    return posts, basket_article_list_serializer


# @get('/dashboard/posts/judged')


@post('/v1/posts')
def create_post():
    # user = get_user_or_401()
    args = create_post_validator(plain_forms())

    # compute article summary.
    article_summary = get_text_from_tag(args['article_content'])

    post_id = short_uuid()
    author = Authors.get(Authors.author_id == 1)

    body = {
        'post_id': post_id,
        'post_status': args.get('post_status') or PostStatusEnum.UNFINISHED_POST.value,
        'post_type': args.get('post_type') or PostTypeEnum.ORIGINAL_POST.value,
        'show_status': args.get('show_status') or ShowStatusEnum.SECRET_POST.value,
        'is_top': args.get('is_top') or False,
        'judge_status': args.get('judge_status') or JudgeStatusEnum.NOT_JUDGE.value,
        'author': author.author_id,
        'category': args['category'],
        'article_title': args['article_title'],
        'article_summary': article_summary,
        'cover': args['cover'],
    }

    with db.atomic():

        BasketArticleList.create(**body)

        del body['article_summary']
        body['article_content'] = args['article_content']

        PoolArticle.create(**body)

    app = default_app()
    es_ = Elasticsearch(app.config['es.host'])

    body = {
        'article_cover': args['cover'],
        'article_summary': article_summary,
        'post_date': datetime.now(),
        'author_id': author.author_id,
        'author_name': author.author_name,
        'author_avatar': author.author_avatar,
        'post_comment_count': 0,
        'post_like_count': 0,
    }

    es_.index(index='pool_articles', doc_type='info', id=post_id, body=body)

    return {'post_id': post_id}
