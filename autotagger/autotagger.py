#!/usr/bin/env python3
#
# python version of
# svoboda autotagger program
#
# authors:
## joshua crowgey
## rachel elle brown
## victoria wellington
## kelsie haakenson
## justin yoon
## ... (add your names as you edit this file)

import sys
import re
import logging
import argparse
from xml.dom.minidom import *

##class constants
CURRENT_VERSION = 1.0
version = -1

## overall regexes
PAGE_RE = re.compile('^Page\s+(\d+)')
PARA_RE = re.compile('^\s+(\S+)')
EMPTYLINE_RE = re.compile('^\s*$')
AMP_RE = re.compile('\&')
VERSION_RE = re.compile('\s*version == (.*)') #for determining if uprev is needed
# regexes for incorrect formatting (e.g. Line #, #, #:)
MARGINLINELIST_RE = re.compile('\s*Line\s+(\d+),') ##change to line list (for journeys too)
MARGINLINERANGE_RE = re.compile('\s*Line\s+(\d+)-')
PAGENOTES_RE = re.compile('^Pages?\s+(\d+)\s*-')
PAGETABBED_RE = re.compile('^\s+Page\s+(\d+)')
TEXTLINE_RE = re.compile('\s*Line\s+(\d+):?\s*(.*)$') # change just to line or something
LINE_RE = re.compile('\s*Line\s+(\d+):?\s*(.*)$')

## version 0 regexes
DIVLINE_RE = re.compile('\s*DivLine:?\s*(.*)$', re.IGNORECASE)
MARGINLINE_RE = re.compile('\s*Line\s+(\d+):?\s*(.*)$') #should combine Margin and Text line regexes
STAR_RE = re.compile('^\s*\*(.*)$')
MARGINS_RE = re.compile('\s*Margins?:?', re.IGNORECASE)
#new regexes looking for "Text:" or the "Line #:" indicating trip headings in body text
TEXT_RE = re.compile('\s*Text:?') #\s*\n^\s*Line\s+(\d+):?\s*(.*)$')


## version 1 regexes
NOTES_RE = re.compile('^\s*Notes:?', re.IGNORECASE)
MARGINNOTE_RE = re.compile('^\s*Margin\s+Line\s+(\d+):?\s*(.*)$')
FOOTNOTE_RE = re.compile('^\s*Footnote:?\s*(.*)$')
SECTION_RE = re.compile('^\s*Section:?')
SUBSECTION_RE = re.compile('^\s*SubSection:?')

def create_respSt(document):
  resp_statement = document.createElement('respStmt')
  resp = document.createElement('resp')
  resp_statement.appendChild(resp)
  resp.appendChild(document.createTextNode('OTAP'))
  name = document.createElement('name')
  resp_statement.appendChild(name)
  name.appendChild(document.createTextNode('Walter Andrews'))
  return resp_statement

def create_teiHeader(document):
  header = document.createElement('teiHeader')
  fileDesc = document.createElement('fileDesc')
  header.appendChild(fileDesc)
  title_statement = document.createElement('titleStmt')
  fileDesc.appendChild(title_statement)

  title = document.createElement('title')
  title_statement.appendChild(title)
  title.appendChild(document.createTextNode('Diary 48'))

  author =  document.createElement('author')
  title_statement.appendChild(author)
  author.appendChild(document.createTextNode('Joseph Mathia Svoboda'))

  title_statement.appendChild(create_respSt(document))

  pubSt = document.createElement('publicationStmt')
  fileDesc.appendChild(pubSt)
  distributor = document.createElement('distributor')
  pubSt.appendChild(distributor)
  distributor.appendChild(document.createTextNode('OTAP'))

  address = document.createElement('address')
  pubSt.appendChild(address)
  addrLine = document.createElement('addrLine')
  address.appendChild(addrLine)

  idno = document.createElement('idno')
  pubSt.appendChild(idno)
  idno.setAttribute('type', 'OTAP')
  idno.appendChild(document.createTextNode('1898-1899'))

  availability = document.createElement('availability')
  pubSt.appendChild(availability)
  p = document.createElement('p')
  availability.appendChild(p)
  p.appendChild(document.createTextNode('Copyright 2012 OTAP. All Rights Reserved.'))

  date = document.createElement('date')
  pubSt.appendChild(date)
  date.setAttribute('when', '2007')
  date.appendChild(document.createTextNode('2011'))

  sourceDesc = document.createElement('sourceDesc')
  fileDesc.appendChild(sourceDesc)
  bibl = document.createElement('bibl')
  sourceDesc.appendChild(bibl)
  bibl.appendChild(document.createTextNode('Joseph Mathia Svoboda'))

  encodingDesc = document.createElement('encodingDesc')
  header.appendChild(encodingDesc)
  projectDesc = document.createElement('projectDesc')
  encodingDesc.appendChild(projectDesc)
  p2 = document.createElement('p')
  projectDesc.appendChild(p2)
  p2.appendChild(document.createTextNode('OTAP'))

  revisionDesc = document.createElement('revisionDesc')
  header.appendChild(revisionDesc)

  listNode = document.createElement('list')
  revisionDesc.appendChild(listNode)

  item = document.createElement('item')
  listNode.appendChild(item)

  date = document.createElement('date')
  item.appendChild(date)
  date.setAttribute('when', '2012-30-08')
  date.appendChild(document.createTextNode('30 August 12'))
  item.appendChild(document.createTextNode('Last checked'))
  return header


def setup_DOM():
  impl = getDOMImplementation()
  doctype = impl.createDocumentType('TEI',None,'http://www.tei-c.org/release/xml/tei/custom/schema/dtd/tei_all.dtd')

  newdoc = impl.createDocument(None, "TEI", doctype)
  document = newdoc.documentElement
  newdoc.appendChild(document)
  teiHeader = create_teiHeader(newdoc)
  document.appendChild(teiHeader)

  text = newdoc.createElement('text')
  document.appendChild(text)

#front = newdoc.createElement('front')
#text.appendChild(front)
#back = newdoc.createElement('back')
#text.appendChild(back)
  body = newdoc.createElement('body')
  text.appendChild(body)
  return newdoc

class TranscriptionFile:
  """class to parse and hold a series of TranscriptionPage objects"""

  pages = []
  errors = []
  version = -1

  def __init__(self, lines):
    self.parse_lines(lines)

  def parse_lines(self, lines):
    """method to parse the lines from the transcription file into
       a series of Transcription Page objects"""
    p = []
    n = -1
    #version = -1
    while len(lines) > 0:
      m1 = PAGE_RE.match(lines[0])
      m2 = PAGENOTES_RE.match(lines[0])
      m3 = PAGETABBED_RE.match(lines[0])
      m4 = VERSION_RE.match(lines[0])
      if n == -1:
        if m4:
          self.version = float(m4.group(1))
          #print("version check in tf: " + str(self.version), file=sys.stderr)
        else:
          version = 0        
      #print("version check in tf after if statement: " + str(self.version), file=sys.stderr)
      if m2:
        self.errors.append(errors(m2.group(1), -1, lines[0], 5))
      if m1:
        # m.group(0) should be the entire matching string
        # m.group(1) should be the page number
        # if n==-1, we're on the first page, so keep going
        # if n is already defined, we've found a new page, so
        #    process the old one
        if n > -1:
          # print(m1.group(1) + " found page", file=sys.stderr)
          self.pages.append(TranscriptionPage(str(n), p, self.version))
          p = []
          lines.pop(0)
          n = int(m1.group(1))
        else:
          n = int(m1.group(1))
          lines.pop(0)
      elif m3:
        self.errors.append(errors(m3.group(1), -1, lines[0], 5))
        self.pages.append(TranscriptionPage(str(n), p, self.version))
        p = []
        n = int(m3.group(1))
        lines.pop(0)
      else:
        p.append(lines[0])
        lines.pop(0)
        

   # try:
    tp = TranscriptionPage(str(n), p, self.version)
    if len(tp.errors) > 0:
      self.errors.extend(tp.errors)
    self.pages.append(tp)
    #except:
     # """Error with page creation. There is not another page to append."""
     
  

class TranscriptionPage:
  """class to hold a transcription page in a nice object
     it has a 'number', a 'header', and a 'body'

     the number should be a positive integer (or zero?, maybe?)
     the header and body are just lists of lines"""

  num = -1
  head = []
  body = []
  errors = []
  version = -1

  def __init__(self, num, lines, version):

    # sys.stderr.write("process transcription page ... ")
    self.num = num
    self.version = version
    self.parse_lines(lines)
    # print(self.num + " page created", file=sys.stderr)

    # check

    # print("[done]\npage info:",file=sys.stderr)
    # print("number: "+self.num,file=sys.stderr)
    # print("header: \n"+str(self.head),file=sys.stderr)
    # print("body: \n"+str(self.body)+"\n", file=sys.stderr)


  def parse_lines(self, lines):
    """header is all lines up to the first empty one, rest is body"""
    #print("version check in tfp parse lines: " + str(self.version), file=sys.stderr)
    if self.version < CURRENT_VERSION:
      self.uprev(lines)
    else:
      h = []
      b = []
      switch = False #false means we're still in head
                   #true means we've switched to body    length = len(lines)
      length = len(lines)
      section = False #true if previous line was Section:
      subsection = False #true if previous line was Subsection:
      multi_headers = False #true if multiple "Lines" are allowed
      divlines = 0
      empty = False #true if previous line in body was empty
      double_spacing = 0 #number of double spaced lines found in body
      double_spacing_found = False #true if double spacing found
      linecount = 0
      for i in range(0, length):
        m1 = NOTES_RE.match(lines[i])
        m2 = MARGINNOTE_RE.match(lines[i])
        m3 = FOOTNOTE_RE.match(lines[i])
        m4 = LINE_RE.match(lines[i])
        m7 = MARGINLINELIST_RE.match(lines[i])
        m8 = MARGINLINERANGE_RE.match(lines[i])
        if m7 or m8:
          self.errors.append(errors(self.num, i, lines[i], 4))
        elif not switch:
          if m1 or m2 or m3:
            h.append(lines[i].rstrip())
          elif lines[i].strip() == "":
            switch = True
          else:
            self.errors.append(errors(self.num, i, lines[i], 1))
        else: #in body
          #do we need this linecount? I don't think so...
          linecount = linecount + 1
          if double_spacing == 3 and double_spacing_found == False:
            logging.warning(" There may be unintentional double spacing on page " + self.num + ".") 
            double_spacing_found = True
          elif double_spacing < 3:
            if lines[i].strip() == "":
              empty = True
            elif empty == True:
              double_spacing += 1
              empty = False
            elif empty == False:
              double_spacing = 0    
          if section or subsection:
            if m4:
              b.append(lines[i])
              multi_headers = True
            else:
              self.errors.append(errors(self.num, i, lines[i], 3))
            if section:
              section = False
            else:
              subsection = False
          else:
            m5 = SECTION_RE.match(lines[i])
            m6 = SUBSECTION_RE.match(lines[i])
            if m5 or m6:
              if m5:
                section = True
                #linecount = linecount - 1
              else:
                subsection = True
              b.append(lines[i].rstrip()) #could pose a problem adding multiple lines.
            elif multi_headers and m4:
              b.append(lines[i].rstrip())
            elif m1 or m2 or m3 or m4:
              self.errors.append(errors(self.num, i, lines[i], 2))
            else:
              b.append(lines[i].rstrip())
              multi_headers = False
      #if divlines != 0:
        #self.errors.append(incorrect_stars_error(self.num))
      self.head = h
      self.body = b
      
      self.printAfter()


  def print(self, lines):
    if self.num == '1': # what if different starting number? Account for that with a variable? 
      print('version == ' + str(CURRENT_VERSION), file=sys.stderr)
    print('Page ' + self.num + ':', file=sys.stderr)
    for l in lines:
      print(l, file=sys.stderr)
   
  def printAfter(self):
    if self.num == '1': # what if different starting number? Account for that with a variable? 
      print('version == ' + str(CURRENT_VERSION), file=sys.stderr)
    print('Page ' + self.num + ':', file=sys.stderr)
    for l in self.head:
      print(l, file=sys.stderr)
    print('', file=sys.stderr)
    for l in self.body:
      print(l, file=sys.stderr)
            
  def uprev(self, lines):
    #why does this introduce tons of double spaces (new lines) to the file?
    #self.print(lines)
    self.bump(lines)
    self.printAfter()

  def bump(self, lines):
    #print("version check in tfp bump lines " + str(self.version), file=sys.stderr)
    if self.version == 0:
      temp_div_headers = [] 
      h = []
      b = []
      switch = False #false means we're still in head
                 #true means we've switched to body    length = len(lines)
      length = len(lines)
      text = False #true if previous line was Text:
      multi_headers = False #true if multiple "Lines" are allowed
      divlines = 0
      empty = False #true if previous line in body was empty
      double_spacing = 0 #number of double spaced lines found in body
      double_spacing_found = False #true if double spacing found
      linecount = 0
      for i in range(0, length):
        m1 = MARGINS_RE.match(lines[i])
        m2 = DIVLINE_RE.match(lines[i])
        m3 = MARGINLINE_RE.match(lines[i])
        m5 = MARGINLINELIST_RE.match(lines[i])
        m6 = MARGINLINERANGE_RE.match(lines[i])
        if m5 or m6:
          self.errors.append(errors(self.num, i, lines[i], 4))
        elif not switch: #in head
          if m1 or m3:
            if m1:
              #lines[i] = re.sub('\s*Margins?:?','\tNotes:',lines[i])
              lines[i] = '\tNotes:'
              #print("Margin to Note" + lines[i], file=sys.stderr)
            if m3:
              #print(lines[i])
              lines[i] = re.sub('^\s*', '\tMargin ', lines[i])
              #adds a new \n character in for some reason...why?
              #print(lines[i])
              #print("Margin added to Line#" + lines[i], file=sys.stderr)
            h.append(lines[i].rstrip())
          elif m2:
              temp_div_headers.append(m2.group(1))
              #lines[i] = ""
              divlines += 1
          elif lines[i].strip() == "":
            switch = True
          else:
            self.errors.append(errors(self.num, i, lines[i], 1))
        else: #in body
          linecount = linecount + 1
          #if linecount == 1:
           # b.append('version = 1')
          if double_spacing == 3 and double_spacing_found == False:
            logging.warning(" There may be unintentional double spacing on page " + self.num + ".") 
            double_spacing_found = True
          elif double_spacing < 3:
            if lines[i].strip() == "":
              empty = True
            elif empty == True:
              double_spacing += 1
              empty = False
            elif empty == False:
              double_spacing = 0    
          if text:
            if m3:
              b.append(lines[i].rstrip())
              multi_headers = True
            else:
              self.errors.append(errors(self.num, i, lines[i], 3))
            text = False
          else:
            m4 = TEXT_RE.match(lines[i])
            m7 = STAR_RE.match(lines[i])
            if m4 or m7:
              if m4:
                text = True
                lines[i] = '\tSection'
                linecount = linecount - 1
              elif m7:
                divlines -= 1
                b.append('\tSubsection:')
                b.append('\tLine ' + str(linecount) + ': ' + temp_div_headers[0])
                temp_div_headers.pop(0)
              lines[i] = re.sub('\*', '', lines[i]) #removes *, need to remove that later in code since not here
              b.append(lines[i].rstrip()) #could pose a problem adding multiple lines.
            elif multi_headers and m3:
              b.append(lines[i].rstrip())
            elif m1 or m2 or m3:
              self.errors.append(errors(self.num, i, lines[i], 2))
            else:
              b.append(lines[i].rstrip())
              multi_headers = False
      if divlines != 0:
        self.errors.append(incorrect_stars_error(self.num))
      self.head = h
      self.body = b

def incorrect_stars_error(page_num):
  """Produces an error message saying there are too many or too few
  asterisks. Contains the page number."""

  return "The number of asterisks in the body does not match the number"+\
         "of DivLines in the header on page "+ page_num +"."

def errors(page_num, line_num, line, error_code):
  """Produces an error message. Contains the line and page number, the
  faulty line, and what the error is."""

  err_str = "An error was found on page " + str(page_num) +\
            ", line " +  str(line_num + 1) + ": " + line.strip()

  if error_code == 1:
    err_str += "Error with head section. Please add either \"Line #\" "+\
               "or \"DivLine\" to the indicated line.\nPlease make sure"+\
               " to format these exactly as shown.\n" +\
               "If this line belongs in the body, please remember to put"+\
               " a space before it.\n"
  elif error_code == 2:
    err_str += "This line belongs in the head. If you meant for this to "+\
               "be in the head," +\
               " there may be an issue with the spacing.\nMake sure there "+\
               "are no spaces between the lines \"Page #:\" and \"Margin:\""+\
               " and that you don't use double spacing.\n"+\
               "If this is a diary entry header, make sure to use \"*\" " +\
               "rather than \"DivLine\".\nIf this is a journey header, add "+\
               " the line \"Text:\" before it.\n"
  elif error_code == 3:
    err_str += "This line should be a journey header. If it is, please make "+\
               "sure to begin it with \"Line #\". If not, please put in a "+\
               "journey header before this line."
  elif error_code == 4:
    err_str += "Lines cannot be formatted like \"Line #, #, #:\" or "+\
               "\"Lines #-#\" or any similar format.\nEach part of the"+\
               "line must get its own line and must begin with \"Line #:\".\n"
  elif error_code == 5:
    err_str += "This line must be formatted \"Page #\". No additional "+\
               "formatting is allowed.\n"
  return err_str

def create_div1(document,n):
  div1 = document.createElement('div1')
  div1.setAttribute('type','journey')
  div1.setAttribute('n',n)
  head = document.createElement('head')
  div1.appendChild(head)
  head.setAttribute('type','journey')
  return head, div1

def create_div2(document,n,part,content):
  div2 = document.createElement('div2')
  div2.setAttribute('type','diaryentry')
  div2.setAttribute('n',n)
  div2.setAttribute('part', part)

  head = document.createElement('head')
  div2.appendChild(head)
  head.setAttribute('type','diaryentry')

  text = document.createTextNode(content)
  head.appendChild(text)
  return div2

def create_p(document,current_prose, first_line=None, fresh=False):
  '''method to create a paragraph, needs the list of paragraphs
     possibly also receive a first line (and it's linenum in a list of len 2).
     fresh tells us whether to empty the list before we start'''
  if fresh: current_prose = []
  current_prose.append(document.createElement('p'))
  if first_line != None:
    lb = document.createElement('lb')
    lb.setAttribute('n',str(first_line[1]))
    current_prose[-1].appendChild(document.createTextNode(first_line[0]))
    current_prose[-1].appendChild(lb)
  return current_prose


def process_id(dict, id, element_type):        
    if id in dict:
      duplicates = dict[value]
      if element_type in duplicates:
        if element_type = 'm':
          logging.warning(" Duplicate marginnote id found: " + id + ". There may be duplicate pages in the Transcription File.")
        elif element_type = 'j':
          logging.warning(" Duplicate journey id found: " + id + ". There may be duplicate pages in the Transcription File.")
        else:
          logging.warning(" Duplicate footnote id found: " + id + ". There may be duplicate pages in the Transcription File.")
      duplicates += element_type
      dict[id] = duplicates
      for i in duplicates.len() - 1:
        value += 'i'
    else:
      dict[id] = element_type
    return id
    
def create_dom_nodes(doc,tf):
  """function that sets up in a DOM form with the nodes: Document, header and body,
  header type divlines and trip titles, margin notes and text"""

  #div2s = [] # contains all diary div headers
  marginheaders = []# triples: [content,pagenum,linenum]
  footnotes = [] # doubles: [content, pagenum]
  xml_ids_dict = {}
  margins = [] #what is this?

  #div1_count = 1
  #div2_printed_count = 1
  #div2_count = 1
  marginline_count = 1
  for page in tf.pages:
    for l in page.head:
       # DivLine: "..." are 'diaryentry' headers
       # Line: "..." are 'margin_note' headers
      m = NOTES_RE.match(l)
      if m:
        continue

      #if len(div2s)==0:
        ## create first div2
        #part = "N"
       # div2s.append(create_div2(doc,str(div2_count),part,"First diary entry, no title given in text."))
      #  div2_count += 1
        #print("div2s header count" + str(len(div2s)), file=sys.stderr)

     # m = DIVLINE_RE.match(l)
      #if m:
        # matched a Divline, create a new div2
       # part="N" # what's part="N"? I though these values were "I" and "F"
        #div2s.append(create_div2(doc,str(div2_count),part,m.group(1)))
        #print("d " + str(page.num) + " " + m.group(1), file=sys.stderr)
       # div2_printed_count += 1
       # div2_count += 1

     # else:
      m = MARGINNOTE_RE.match(l)
      if m:
        head = doc.createElement('head')
        marginheaders.append([head, page.num, m.group(1)])
        head.setAttribute('type','marginnote')
        marginnote_id = "p" + page.num + '-' + m.group(1)
        #need to figure out a way to make it so dict can record if there is both a journey
        # and margin id for this number.
        
        marginnote_id = process_id(xml_ids_dict, marginnote_id, 'm')

        head.setAttribute('xml:id', marginnote_id) # could factor out all process of
        # creating and assigning xml id, or creating headers in general eventually.
        text = doc.createTextNode(m.group(2))
        head.appendChild(text)
      
      m = FOOTNOTE_RE.match(l)
      #factor out head creation code?
      if m:
        head = doc.createElement('head')
        footnotes.append([head, page.num])
        head.setAttribute('type', 'footnote')
        footnote_id = "p" + page.num 
        footnote_id process_id(xml_ids_dict, footnote_id, 'f')
        head.setAttribute('xml:id', footnote_id) # could factor out all process of
        # creating and assigning xml id, or creating headers in general eventually.
        text = doc.createTextNode(m.group(1))
        head.appendChild(text)

  if len(div2s)==0:
    ## create first div2 if there is no header, and therefore still are no div2s.
    part = "N"
    div2s.append(create_div2(doc,str(div2_count),part,"First diary entry, no title given in text."))
    div2_count += 1
    #print("div2s at end of create dom nodes method count" + str(len(div2s)), file=sys.stderr)
  return marginheaders, footnotes, xml_ids_dict

def organize_nodes(document, tf, marginheaders, footnotes, xml_ids_dict):
  # this will be a list of paragraph nodes
  current_prose = []
  current_prose = create_p(document,current_prose)
  div1s = [] # contains all trip div headers
  div2s = [] # contains all diary div headers

  # get document body to appending below
  body = document.getElementsByTagName('body')[0]

  #new_trip = False
  empty_lines = 0
  last_empty = False

  current_div1 = None
  previous_text = False
  current_head = None
  text_found = False
  div1_count = 1
  # need line number stored in an attribute?
  for page in tf.pages:
    #if page.num == "1":
    if current_div1 == None:
      current_head, div1 = create_div1(document, str(div1_count))
      current_div1 = div1
      text = document.createTextNode("First Journey in Diary; No Journey Title")
      current_head.appendChild(text)
      div1_count += 1
      current_div1.appendChild(div2s[0])

    linecount = 0
    for l in page.body:
      #if "Text:" matched and if "Line #:" is found right after "Text:", or it
      #is the first line of the entire file, create a div 1 and add it to the list div1s
      m = TEXT_RE.match(l)
      if m:
        text_found = True
        continue
      else:
        linecount += 1
        if len(marginheaders) > 0:
          current_lineheader = marginheaders[0]
          if linecount <= int(current_lineheader[2]) and page.num == current_lineheader[1]:
            div2s[0].appendChild(current_lineheader[0])
            #marginheaders.pop(0)
            marginheaders.remove(current_lineheader)
        #else:
          #print("ran out of marginheaders",file=sys.stderr)

        #organizing div1s
        m = EMPTYLINE_RE.match(l)
        if m:
          #found empty line
          last_empty = True
          empty_lines += 1
          continue
        elif last_empty:
          for i in range(1, empty_lines + 1):
            lb = document.createElement('lb')
            lb.setAttribute('n',str((linecount - empty_lines + (i - 1))))
            current_prose[-1].appendChild(lb)
          last_empty = False
          empty_lines = 0

        # now looping through page body to find div1s, which we may
        # want to figure out how to do in the organize_nodes method
        # later so as not to loop through the file as much.
        m = TEXTLINE_RE.match(l)
        if m and text_found:
          body.appendChild(current_div1)
          if not previous_text:
            #creates a cloned div2 with all its nodes to serve as the medial
            # or final part then labeled as the next number in the div2_count
            # check and see if the last one was part f. if so make the
            # last one part m instead.
            if len(div2s) >= 1:
              next_div2 = div2s[0].cloneNode(False)
              next_div2.setAttribute('part', 'F')
              atr = div2s[0].getAttributeNode('part')
              x = atr.nodeValue
              if x == 'F':
                div2s[0].setAttribute('part', 'M')
              else:
                div2s[0].setAttribute('part', 'I')
              div2s[0].childNodes.extend(current_prose)
              current_prose = create_p(document,current_prose, fresh=True)
              current_div1.appendChild(div2s[0])

              if len(div2s) > 1:
                headCheck = div2s[0].getElementsByTagName('head')
                div2s.pop(0)

              #if it is the first line in the file, just create a generic and
              # arbitrary div1 to hold diary entries until the first real div1
              # trip heading is found.
              current_head, div1 = create_div1(document, str(div1_count))
              current_div1 = div1
              div1_count += 1
              div2s.insert(0, next_div2)


            journey_id = "p" + page.num + '-' + m.group(1)
            
            journey_id = process_id(xml_ids_dict, journey_id, 'j')
            
            current_head.setAttribute('xml:id', journey_id)
            
            previous_text = True

            #creates a cloned div2 with all its nodes to serve as the medial or final part
            #then labeled as the next number in the div2_count
              #div2_count += 1

          #if it actually is a trip heading, print the text as the header (and added in the
          #line number here just in case, since I don't know if that is important or not


          text = document.createTextNode(m.group(2))
          current_head.appendChild(text)
          lb = document.createElement("lb")
          lb.setAttribute("n", m.group(1))
          current_head.appendChild(lb)

          continue
        else:
          #text line for trip header isn't matched, variables set accordingly.
          previous_text = False
          text_found = False
        #new_trip = False

        #organizes div2s. This section is the one with the most bugs
        # I think, mainly the part attribute issue
        m = STAR_RE.match(l)
        if m:
          #appends children to div2 and that div2 to div1, then moves to
          # the next div2
          div2s[0].childNodes.extend(current_prose)
          current_div1.appendChild(div2s[0])
          #div1s[current_div1].appendChild(div2s[0])

          # delete the star and add this line to the current paragraph of current prose
          current_prose = create_p(document,current_prose,[re.sub('\s*\*','',l),linecount],fresh=True)
          if len(div2s) > 1:
            headCheck = div2s[0].getElementsByTagName('head')
            div2s.pop(0)
        else:
          m = PARA_RE.match(l)
          if m:
            ## found a paragraph starting line of text
            # start a new paragraph
            current_prose = create_p(document, current_prose,[l,linecount])
          else:
            ## found a vanilla line of text
            lb = document.createElement('lb')
            lb.setAttribute('n',str(linecount))
            current_prose[-1].appendChild(document.createTextNode(l))
            current_prose[-1].appendChild(lb)
    #maybe add in something that says to delete the last line break 
    # before creating the next page to fix that bug?
    last_empty = False
    empty_lines = 0
    pb = document.createElement('pb')
    pb.setAttribute('n',str(page.num))
    current_prose[-1].appendChild(pb)
      # print([c.toxml() for c in current_prose],file=sys.stderr)
  # done looping, everything organized so stick the nodes onto the document
  div2s[0].childNodes.extend(current_prose)
  current_div1.appendChild(div2s[0])
  body.appendChild(current_div1)

def setup_argparse():
  ap = argparse.ArgumentParser()
  ap.add_argument('--file', '-f', help='choose a file for the autotagger')
  ap.add_argument('--verbose', '-v', action='count', dest='verbosity', 
      default=2, help='increase the verbosity (can be repeated: -vvv)') 
  return ap

if __name__ in "__main__":
  # accept svoboda transcription format file
  # on stdin

  ap = setup_argparse()
  args = ap.parse_args()
  if args.file:
    infile = open(args.file, encoding="utf-8")
    infilelines = infile.readlines()
  else:
    infilelines = sys.stdin.readlines()

  logging.basicConfig(format='%(levelname)s:%(message)s',
                          level=50-(args.verbosity*10)) 
  # to keep things clean, and check for errors in
  # the input,
  # before we start, parse these lines
  # into a series of 'page objects'

  tf = TranscriptionFile(infilelines)
  logging.info(" found "+str(len(tf.pages))+" transcription pages")

  #for page in tf.pages:
   # for l in page.head:
    #  print(l)
    #for l in page.body:
     # print(l)
      
  if len(tf.errors) > 0:
    print("Errors found. Please check error log and try again later.")
    for e in tf.errors:
      print(e,file=sys.stderr)
  else:
    document = setup_DOM()
    marginheaders, footnotes, xml_ids_dict = create_dom_nodes(document, tf)
    organize_nodes(document, tf, marginheaders, footnotes, xml_ids_dict)
    print(document.toprettyxml('\t', '\n', None))
