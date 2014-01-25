#! /usr/bin/env python
# coding: utf-8
"""
This file is intended to be used as a line command utility -
its current limtied use-case is to trim  wrongly placed
spaces inside XML tags in the translation of PO files
(it will also fail on incorrect TAGS inside MSGSTRs,
indicating the error line)

Inside it, however, there are fundamentals for
.po files parsing - so more tools could be developed from what
is in here.

"""



from __future__ import unicode_literals

import sys, os
import re

ZERO_WIDTH_SPACE = "\u200b"

class BaseMsg(unicode):

    def __new__(cls, text="", encoding=None, errors=None, starting_line=None):
        # FIXME: not using encoding, errors parameter
        self = unicode.__new__(cls, text)
        self.starting_line = starting_line
        return self

    def text(self):
        """Returns content as a single unicode string"""
        result = ""
        for line in self.split("\n"):
            # removes the whitespace and '"'s from each line
            result += line.strip()[1:-1]
        return self.starting_line, result

    @classmethod
    def format(cls, text, width=60):
        """Naively reformats a paragraph into \" quoted chunks
           having at most the suggested linelenght.
        """
        result = ""
        line = ""
        i = 0
        while i < len(text):
            part = text[i]
            #unescape
            if part == "\\":
                i += 1
                part += text[i]
            elif part.isspace():
                part = " "
            line += part
            if ((len(line) >= width and part == " ") or part == "\\n"):
                result += "\"%s\"\n" % line
                line = ""
            i += 1
        if line:
            result += "\"%s\"\n" %line
        return cls(result)

    def __unicode__(self):
        return self

class Comment(BaseMsg): pass


class MSGID(BaseMsg):
    def __unicode__(self):
        return "msgid " + super(MSGID, self).__unicode__()
        
class MSGSTR(BaseMsg): 
    def __unicode__(self):
        return "msgstr " + super(MSGSTR, self).__unicode__()

def strip_keyword(line):
    if line.startswith("\""):
        return line
    else:
        return "\"" + line.split("\"",1)[-1]

def po_from_str(text):
    b"""Returns the text of a PO file formated like this:
        each block of comments + white space, msgid, or msgstr comes
        as tuple of starting line + an apropriate object. If one simply joins all objects
        as unicode strings, he will have the original file (semantically) back
    """

    inside_msgstr = False
    inside_msgid = False
    tmp_comment = ""
    tmp_msgid = ""
    tmp_msgstr = ""
    parsed_data = []
    text = text.split("\n")
    i = 0
    starting_line = 0
    while i < len(text):
        line = text[i].strip()
        line += "\n"
        if not inside_msgid and not inside_msgstr:
            if not line.startswith(("msgid", "msgstr")):
                tmp_comment += line
            else:
                parsed_data.append(Comment(tmp_comment, starting_line=starting_line + 1))
                tmp_comment = ""
                starting_line = i
                if line.startswith("msgid"):
                    tmp_msgid = strip_keyword(line)
                    inside_msgid = True
                else:
                    tmp_msgstr = strip_keyword(line)
                    inside_msgstr = True
        else:
            if inside_msgid:
                if line.startswith(("msgid", "\"")):
                    tmp_msgid += strip_keyword(line)
                else:
                    # end of msgid
                    inside_msgid = False
                    parsed_data.append(MSGID(tmp_msgid, starting_line=starting_line + 1))
                    tmp_msgid = ""
                    i -= 1
                    starting_line = i
            elif inside_msgstr:
                if line.startswith(("msgstr", "\"")):
                    tmp_msgstr += strip_keyword(line)
                else:
                    # end of msgstr
                    inside_msgstr = False
                    parsed_data.append(MSGSTR(tmp_msgstr, starting_line=starting_line + 1))
                    tmp_msgstr = ""
                    i -= 1
                    starting_line = i

        i += 1
    if tmp_comment:
        if tmp_comment.endswith("\n\n"):
            tmp_comment = tmp_comment[:-1]
        parsed_data.append(Comment(tmp_comment, starting_line=starting_line + 1))
    elif tmp_msgstr:
        parsed_data.append(MSGSTR(tmp_msgstr, starting_line=starting_line + 1))

    return parsed_data
                    



def remove_spaces_inside_tags(text, starting_line=0):
    """
       given a string, if it finds XML tags, removes inner
       spaces inside the tags.
    """
    tag_end = False
    inside_tag = False
    tag_stack = []
    tag_name = ""
    result = ""
    i = 0
    lastchar = ""
    seen_space = False
    tag_name_is_over = False
    while i < len(text):
        part = text[i]
        if not inside_tag and not part == "<":
            # FIXME: we are eating only one space inside tags.
            # let's hope there are not more of them. (or jut run this more times)
            # bail out on unclosed xml tags
            if tag_stack and i == len(text) - 1:
                raise ValueError (b"Malformed xml tag at %d: %s " % (starting_line, text.encode("utf-8")))
            if (tag_stack and part == " " and
                (text[i-1] == ">" or text[i + 1] == "<")
               ):
                #eat bad space
                pass
            else:
                result += part
        elif part == "<":
            name_commited = False
            if not tag_stack and text[i+1] == "/":
                sys.stderr.write(text.encode("utf-8") + b"\n")
                raise ValueError (b"Malformed xml tag at %d: %s " % (starting_line, text.encode("utf-8")))
            inside_tag = True
            tag_name_is_over = False
            seen_space = False
            result += part
            if text[i+1] == "/":
                result += "/"
                i += 1
                tag_end = True
                # One of the programs in the POT chain uses
                # the ZERO_WIDTH_SPACE unicode char after the
                # </ and before the tagname
                # this is extensively annoying, and causes undreadable
                # linebreaks in the sourcecode.
                # here, let's just copy it verbatin. Our output
                # won't break the msgstr at the </ anyway;
                count = 0
                while text[i+1] == ZERO_WIDTH_SPACE:
                    if not count:
                        result += ZERO_WIDTH_SPACE
                        count += 1
                    i += 1
            else:
                tag_end = False
        elif inside_tag:
            result += part
            if not tag_name_is_over and part.isalpha():
                tag_name += part
            else:
                tag_name_is_over = True
                if part.isspace():
                    seen_space = True
                if tag_end:
                    #if not tag_stack:
                    #    raise ValueError (b"Malformed xml tag at %d: %s " %
                    #        (starting_line, text.encode("utf-8")))
                    if not name_commited and tag_name == tag_stack[-1]:
                        tag_stack.pop()
                        name_commited = True
                    elif not name_commited:
                        #print tag_name, tag_stack, """\"%s\"""" % part, len(part)
                        sys.stderr.write(text.encode("utf-8") + b"\n")
                        raise ValueError (b"Mismatched XML tag at  %d: %s " % (starting_line, text.encode("utf-8")))
                else:
                    if not seen_space and part == "@":
                            # this is most likely  an e-mail address, not a xml tag:
                        if name_commited:
                            # some non alpha char in the email address caused
                            # it to be added as a tag (like a number)
                            tag_stack.pop()
                        name_commited = True
                        pass
                    elif not name_commited:
                        tag_stack.append(tag_name)
                        name_commited = True
                if part == ">":
                    inside_tag = False
                    if lastchar == "/":
                        # autoclosing tag
                        tag_stack.pop()
                    tag_name = ""
            lastchar = part

        i += 1
    return result

def main(filename):
    data = open(filename).read().decode(b"utf-8")
    
    parsed_data = po_from_str(data)
    for i, item in enumerate(parsed_data):
        if isinstance(item, MSGSTR):
            starting_line, text = item.text()
            parsed_data[i] = MSGSTR.format(remove_spaces_inside_tags(text, starting_line))
    for item in parsed_data:
        sys.stdout.write(unicode(item).encode("utf-8"))
    #os.rename(filename, filename + b".old")
    

if __name__== "__main__":
    
    try:
        filename = sys.argv[1]
    except IndexError:
        sys.stderr.write ("Use %s <filename> to reformat XML tags in the msgstr part of the text\n")
    main(filename)

