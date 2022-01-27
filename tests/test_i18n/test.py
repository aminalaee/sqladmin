# coding: utf-8

import gettext
import os

for name in ["LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"]:
    if name in os.environ and os.environ[name]:
        print("当前的语言环境是：", os.environ[name])
        break

gettext.bindtextdomain("test_messages", "translations/")
gettext.textdomain("test_messages")

_ = gettext.gettext
print(_("just a test string"))
gettext.textdomain("messages")
print(_("just a test string"))
