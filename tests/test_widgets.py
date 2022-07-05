# -*- coding: utf-8 -*-
from wtforms import Form

from sqladmin.fields import RadioField
from sqladmin.widgets import ListWidget


def test_list_widget():
    choices = [("1", "A"), ("2", "B"), ("3", "C")]

    class F(Form):
        radio = RadioField(choices=choices, coerce=int)

    w = ListWidget()
    html_content = str(w(F().radio))
    assert html_content.count("<div") == 1
    assert html_content.count("<input") == len(choices)

    w2 = ListWidget(html_tag="ul", sub_html_tag="li")
    html_content = str(w2(F().radio))
    assert html_content.count("<ul") == 1
    assert html_content.count("<li") == len(choices)

    w3 = ListWidget(html_tag="ul", sub_html_tag="li", sub_render_kw={"class": "foo"})
    html_content = str(w3(F().radio))
    assert html_content.count("class=foo") == len(choices)
