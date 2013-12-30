# -*- coding: utf-8 -*-
# Author: João S. O. Bueno <gwidion@gmail.com>

# Copyright: 2013, 2014 João S. O. Bueno 
# License GPLv2.0 or Later

import Kross,Lokalize,Project,Editor
import sys,os,time,datetime,re,string,codecs

def get_tags(text):
    matches = re.findall(ur"(<(.+?).*?>.+?</\2\s?>)" , text,
        re.MULTILINE |re.DOTALL)
    tags = [match[0] for match in matches]
    return tags

def replace_inner_text(tag, text):
    return re.sub(ur"[^>]+?</", text + u"</", tag, 1)



def main():
    current_entry = Editor.currentEntry()
    source = Editor.entrySource(current_entry, 0).decode("utf-8")
    target = Editor.entryTarget(current_entry, 0).decode("utf-8")
    source_tags = get_tags(source)
    target_tags = get_tags(target)

    if len(source_tags) - len(target_tags) <= 0: return

    tag_to_insert = source_tags[len(target_tags)]

    selection = Editor.selectionInTarget()

    if selection:
        selection = selection.decode("utf-8")
        tmp = replace_inner_text(tag_to_insert, selection)
        partition = target.rfind(selection)
        target = target[:partition] + target[partition:].replace(selection, tmp)
    else:
        target += tag_to_insert

    Editor.setEntryTarget(current_entry, 0, target.encode("utf-8"))

main()
