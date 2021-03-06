import os, re, configparser
from pickle import FALSE
from dateutil.parser import parse
from urllib.parse import unquote
from functools import partial
import filetype
import time
from csv2md.table import Table
import shutil

def link_replace(cur_dir, matchobj):
  link = matchobj.group(2)
  file = os.path.join(cur_dir, link)
  res = '[{0}]({1})'.format(matchobj.group(1), link)
  if os.path.isfile(file):
    kind = filetype.guess(file)
    old_filename = os.path.split(link)[1].replace(' ', '_')
    if kind is not None and (kind.mime.startswith('image') or kind.extension == '.pdf' ): # guess extension of image as notion export may not come with one. link to pdf files requie a !
      new_filename = '{0}_{1}.{2}'.format(os.path.splitext(old_filename)[0], time.time_ns(), kind.extension)
      shutil.move(file, os.path.join(logseq_assets_dir, new_filename))
      link = '../assets/' + new_filename
      res = '![{0}]({1})'.format(matchobj.group(1), link)
    elif file.endswith('.csv'): # filetype module cannot recognize csv file 
      with open(file, 'rt') as f:
        table = Table.parse_csv(f)
        res = table.markdown().replace('\n', '\n\t')
    else: # otherwise copy to assets directory and make a link to it
      filename_tuple = os.path.splitext(old_filename)
      new_filename = '{0}_{1}.{2}'.format(filename_tuple[0], time.time_ns(), filename_tuple[1])
      shutil.move(file, os.path.join(logseq_assets_dir, new_filename))
      link = '../assets/' + new_filename
      res = '[{0}]({1})'.format(matchobj.group(1), link)
  return res

def notion_walk(notion_dir):
  dir_tag = os.path.basename(notion_dir).split()[0]
  for filename in os.scandir(notion_dir):
    if filename.is_dir():
      csv_file = filename.path + '.csv' # there should be a csv file with corresponding name or it is not a page 
      if os.path.exists(csv_file):
        with open(csv_file, newline='\n') as csvfile:
          if 'Name,Created' in csvfile.readline(): # iterate inner page directory
            notion_walk(filename.path) # skip databases, images directories etc
    elif filename.is_file() and filename.name.endswith('.md'):
      with open(filename.path, 'rt', encoding='utf-8') as input_file:
        print('processing: {}'.format(filename.name))
        lines = input_file.readlines() # get notion pages content
        logseq_block_title = lines[0][2:].strip() # use first line as logseq block title
        logseq_filename = parse(lines[2][9:].strip()).strftime('%Y_%m_%d') + '.md' # use created at date as logseq filename 
        with open(os.path.join(logseq_journals_dir, logseq_filename), 'at', encoding='utf-8') as output_file: # always append to, or create logseq file
          md_code = False
          headless_content = False
          output_file.write('- {0} #{1}\n'.format(logseq_block_title, dir_tag))
          for line in lines:
            if not headless_content:
              if line.startswith('Updated:'): # skip header
                headless_content = True
              continue
            #line_trim = line.replace('    ', '\t') # try to fix indent instead of strip()
            line_trim = line.strip() # remove indent
            if len(line_trim) == 0:
              continue
            if md_link_pattern.search(line_trim):
              line_trim = unquote(line_trim) # unquote urlencoded characters
              line_trim = md_link_pattern.sub(partial(link_replace, notion_dir), line_trim) # replace link text & move png to assets
              line_trim = line_trim.replace('!!', '!') ## sometimes notion images come with ! sometimes not
            if line_trim.startswith('```'): # code snippet
              if not md_code: # first line
                output_file.write('\t- ```\n')
                md_code = True
              else:
                output_file.write('```\n') # last line
                md_code = False
              continue
            if md_code:
              output_file.write('{0}\n'.format(line_trim)) # do not insert - for lines in code snippet
            elif line_trim[0] == '-': # fix indent if this line is an unordered list
              output_file.write('\t{0}\n'.format(line_trim))
            else: 
              output_file.write('\t- {0}\n'.format(line_trim))
    else:
      print('{0} is not a dir nor a file'.format(filename))
      continue

if __name__ == '__main__':
  # Load Configuration
  config = configparser.ConfigParser()
  config.read('config.ini')
  logseq_dir = config['logseq']['Directory']
  logseq_journals_dir = os.path.join(logseq_dir, 'journals')
  logseq_assets_dir = os.path.join(logseq_dir, 'assets')
  notion_export_dir = config['notion']['Directory']

  # Generate regular expressions
  md_link_pattern = re.compile(r'\[(.*)\]\((.*)\)')

  # Iterate through notion directory
  notion_walk(notion_export_dir)