# -*- coding:utf-8 -*-
import os
import re
import json
import pytz
import markdown
import datetime

from flask import Flask, render_template, request, session, url_for, redirect

from .utils import project_path, decode
from .db import DB


app = Flask(__name__)
app.config.from_pyfile(os.path.join(project_path, "settings.py"))
app.static_folder = os.path.join(project_path, app.config.get("STATIC_FOLDER"))
app.static_url_path = app.config.get("STATIC_URL_PATH")
app.template_folder = os.path.join(project_path, app.config.get("TEMPLATE_FOLDER"))
tz = pytz.timezone(app.config.get("TIME_ZONE"))


db = DB(app.config)


@app.route("/")
def index():
    return render_template('index.html', author=app.config.get("AUTHOR"))


@app.route("/import")
def login():
    if not session.get("login"):
        return render_template("login.html", ref="imports")
    else:
        return render_template("imports.html", success="",
                               title=request.form.get("title", ""),
                               tags=request.form.get("tags", ""),
                               description=request.form.get("description", ""),
                               author=request.form.get("author", ""),
                               feature=request.form.get("feature"),
                               id=request.form.get("id", ""))


@app.route('/check', methods=["post"])
def check():
    ref = request.form.get("ref")
    if request.form.get("username") == app.config.get("USERNAME") and request.form.get("password") == app.config.get("PASSWORD"):
        session["login"] = "%s:%s"%(request.form.get("username"), request.form.get("password"))
        return render_template("%s.html"%ref, success="",
                               title=request.form.get("title", ""),
                               tags=request.form.get("tags", ""),
                               description=request.form.get("description", ""),
                               author=request.form.get("author", ""),
                               feature=request.form.get("feature"),
                               id=request.form.get("id", ""),
                               ref=ref,
                               article=db.gen_article(app.config.get("INDEX"), app.config.get("DOC_TYPE"), request.form.get("id")))
    else:
        return render_template("login.html", title=request.form.get("title", ""),
                               tags=request.form.get("tags", ""),
                               description=request.form.get("description", ""),
                               author=request.form.get("author", ""),
                               feature=request.form.get("feature"),
                               id=request.form.get("id", ""),
                               ref=ref)


@app.route("/imports", methods=["post"])
def imports():
    if not session.get("login"):
        return render_template("login.html", ref="imports")
    file = request.files["article"]
    title = request.form.get("title")
    article = decode(file.read())
    author = request.form.get("author") or app.config.get("AUTHOR")
    tags = request.form.get("tags").split(",")
    feature = eval(request.form.get("feature", "False"))
    description = request.form.get("description")
    id = datetime.datetime.now(tz).strftime("%Y%m%d%H%M%S")
    body = {
        "id": id,
        "tags": tags,
        "description": description,
        "title": title or file.filename.replace(".md", ""),
        "article": article,
        "author": author,
        "feature": feature,
        "created_at": datetime.datetime.now(tz),
        "updated_at": datetime.datetime.now(tz),
        "show": 1,
    }
    db.index(app.config.get("INDEX"), app.config.get("DOC_TYPE"), id=id, body=body)
    return render_template("imports.html", success="success")


@app.route("/edit")
def edit():
    id = request.args.get("id")
    doc = db.get(app.config.get("INDEX"), id=id, doc_type=app.config.get("DOC_TYPE"))
    doc["_source"]["tags"] = ",".join(doc["_source"]["tags"])
    if not session.get("login"):
        return render_template("login.html", ref="edit", **doc["_source"])
    return render_template("edit.html", ref="update", **doc["_source"])


@app.route("/update", methods=["post"])
def update():
    if not session.get("login"):
        return render_template("login.html", ref="imports")
    article = request.form.get("article")
    id = request.form.get("id")
    title = request.form.get("title")
    author = request.form.get("author") or app.config.get("AUTHOR")
    tags = request.form.get("tags").split(",")
    feature = eval(request.form.get("feature", "False"))
    description = request.form.get("description")
    body = {
        "doc": {
            "tags": tags,
            "description": description,
            "title": title,
            "article": article,
            "author": author,
            "feature": feature,
            "updated_at": datetime.datetime.now(tz),
        }
    }
    db.update(app.config.get("INDEX"), app.config.get("DOC_TYPE"), id=id, body=body)
    return redirect(url_for("index"))


@app.route("/delete")
def delete():
    if not session.get("login"):
        return render_template("login.html", ref="delete", id=request.args.get("id", ""))
    db.delete(app.config.get("INDEX"), id=request.args.get("id"), doc_type=app.config.get("DOC_TYPE"))
    return redirect(url_for("index"))


@app.route("/article")
def article():
    article = db.get(app.config.get("INDEX"), app.config.get("DOC_TYPE"), request.args.get("id"))
    format_article_body = markdown.markdown(article["_source"]["article"], extensions=['markdown.extensions.extra'])
    _, articles = format_articles([article])
    article = articles[0]
    article["article"] = format_article_body
    return json.dumps(article)


@app.route("/me")
def me():
    id = "me"
    article = db.get(app.config.get("INDEX"), app.config.get("DOC_TYPE"), id)
    if article:
        article = article["_source"]
    else:
        created_at = datetime.datetime.now(tz)
        article = {"id": id,
               "author": app.config.get("AUTHOR"),
               "tags": [id],
               "description": id,
               "feature": 0,
               "article": id,
               "title": id,
               "show": 0,
               "updated_at": created_at,
               "created_at": created_at}
        db.index(app.config.get("INDEX"), app.config.get("DOC_TYPE"), id, article)
        article["updated_at"] = created_at.strftime("%Y-%m-%dT%H:%M:%S")
        article["created_at"] = created_at.strftime("%Y-%m-%dT%H:%M:%S")
    article["article"] = markdown.markdown(article["article"],
                                        extensions=['markdown.extensions.extra'])
    return json.dumps(article)


@app.route("/contact")
def contact():
    id = "contact"
    article = db.get(app.config.get("INDEX"), app.config.get("DOC_TYPE"), id)
    if article:
        article = article["_source"]
    else:
        created_at = datetime.datetime.now(tz)
        article = {"id": id,
                   "author": app.config.get("AUTHOR"),
                   "tags": [id],
                   "description": id,
                   "feature": 0,
                   "article": id,
                   "title": id,
                   "show": 0,
                   "updated_at": created_at,
                   "created_at": created_at}
        db.index(app.config.get("INDEX"), app.config.get("DOC_TYPE"), id, article)
        article["updated_at"] = created_at.strftime("%Y-%m-%dT%H:%M:%S")
        article["created_at"] = created_at.strftime("%Y-%m-%dT%H:%M:%S")
    article["article"] = markdown.markdown(article["article"],
                                        extensions=['markdown.extensions.extra'])
    return json.dumps(article)


def format_articles(articles):
    tags = {}
    format_articles = []
    for article in articles:
        article = article["_source"]
        mth = re.search(r"\!\[.*?\]\((.*?)\)", article.pop("article"))
        article["first_img"] = mth.group(1) if mth else ""
        for tag in article["tags"]:
            tags[tag.upper()] = tags.setdefault(tag.upper(), 0) + 1
        format_articles.append(article)
    return tags, format_articles


@app.route("/show")
def show():
    count, articles, feature_articles = db.search(app.config.get("INDEX"), app.config.get("DOC_TYPE"),
                         request.args.get("searchField"), request.args.get("from", 0),
                         request.args.get("size", 20))
    tags, articles = format_articles(articles)
    _, feature_articles = format_articles(feature_articles)
    return json.dumps({"count": count, "articles": articles, "feature_articles": feature_articles,
                       "tags": [i[0] for i in sorted(tags.items(), key=lambda x: x[1], reverse=True)]})