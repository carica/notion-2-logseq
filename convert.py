import os, re, configparser
from dateutil.parser import parse
from urllib.parse import unquote
from functools import partial

def link_replace(cur_dir, matchobj):
  link = matchobj.group(2)
  if link.endswith('.png'):
    file = os.path.join(cur_dir, link)
    new_filename = os.path.split(link)[1].replace(' ', '_')
    os.rename(file, os.path.join(logseq_assets_dir, new_filename))
    link = '../assets/' + new_filename
  return '[{0}]({1})'.format(matchobj.group(1), link)

def notion_walk(notion_dir):
  for filename in os.scandir(notion_dir):
    if filename.is_dir():
      csv_file = filename.path + '.csv' # there should be a csv file with corresponding name or it is not a page 
      if os.path.exists(csv_file):
        with open(csv_file, newline='\n') as csvfile:
          if 'Name,Created,Tags,Updated' in csvfile.readline(): # iterate inner page directory
            notion_walk(filename.path) # skip databases, images directories etc
    elif filename.is_file() and filename.name.endswith('.md'):
      with open(filename.path, 'rt', encoding='utf-8') as input_file:
        lines = input_file.readlines() # get notion pages content
        logseq_block_title = lines[0][2:].strip() # use first line as logseq block title
        logseq_filename = parse(lines[2][9:].strip()).strftime('%Y_%m_%d') + '.md' # use created at date as logseq filename 
        with open(os.path.join(logseq_journals_dir, logseq_filename), 'at', encoding='utf-8') as output_file: # always append to, or create logseq file
          output_file.write('- {0}\n'.format(logseq_block_title))
          headless_input = lines[4:] # skip first 4 lines
          for line in headless_input:
            line_trim = line.strip()
            if len(line_trim) == 0:
              continue
            if md_link_pattern.search(line_trim):
              line_trim = unquote(line_trim) # unquote urlencoded characters
              line_trim = md_link_pattern.sub(partial(link_replace, notion_dir), line_trim) # replace link text & move png to assets
            if line_trim[0] == '-':
              output_file.write('\t{0}\n'.format(line_trim))
            else: 
              output_file.write('\t- {0}\n'.format(line_trim))
    else:
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