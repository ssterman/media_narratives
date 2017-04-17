#######################################################

#  Retrieves articles from Berkeleyside news site for analysis
#  Please do not change the 5 second delays, so as not to overwhelm site
#
#  Code is based off ssterman and radiolarian 's AO3 scraper 
#  written by ssterman

# Two types of usage:  get ids and urls, or input a csv with ids and urls to get article data
# usage:

# python berkeleyside_scraper.py --outcsv city_urls
# python berkeleyside_scraper.py city_article_urls.csv --outcsv city_articles 

#######################################################


from bs4 import BeautifulSoup
import re
import time
import requests
import csv
import sys
import datetime
import argparse
from unidecode import unidecode


base_url = "http://www.berkeleyside.com"
categories = ["city", "arts", "business", "community", "crime-safety", "schools"] #, "obituaries", "opinion", "nosh", "real-estate"]
cur_page = 1
seen_id_list = []

#######################################################

# Basic usage

#######################################################

def get_args(): 
	parser = argparse.ArgumentParser(description='Scrape and save articles from berkeleyside, given URL.')
	parser.add_argument(
		'incsv', metavar='IN_CSV', nargs='?',
		help='a csv input filename')
	parser.add_argument(
		'--outcsv', default='articles.csv',
		help='csv output file name')
	parser.add_argument(
		'--header', default='',
		help='user http header')
	parser.add_argument(
		'--restart', default='', 
		help='article_id to restart at (inclusive) from within a csv')
	args = parser.parse_args()
	csv_out = str(args.outcsv)
	headers = str(args.header)
	restart = str(args.restart)
	return args.incsv, csv_out, headers, restart


def make_readme(csv_name):
	with open(csv_name + "_readme.txt", "w") as text_file:
		text_file.write(csv_name + " was retreived on: " + str(datetime.datetime.now()))

def get_soup(url, responsiveness):
	req = requests.get(url)
	soup = BeautifulSoup(req.text, "lxml")
	# some responsiveness in the "UI"
	sys.stdout.write('.' + responsiveness + '.')
	sys.stdout.flush()
	return soup

#######################################################
# These functions will generate the [id, url] csv
# URL
# Article ID
# 	id="post-253211"
#######################################################

def write_to_csv(ids, urls, csv_name):
	with open(csv_name + ".csv", 'a') as csvfile:
		wr = csv.writer(csvfile, delimiter=',')
		for i in range(0, len(ids)):
			wr.writerow([ids[i], urls[i]])

def get_ids(soup):
	urls = []
	entries = soup.find_all(class_ = "entry-title")
	for e in entries:
		urls.append(e.contents[0].get('href'))

	articles = soup.find_all('article')
	ids = []
	for a in articles:
		id_ = a.get('id')
		id_ = id_[5:]
		ids.append(id_)

	# pubdates = soup.find_all(class_ = "entry-date published")
	# dates = []
	# for d in pubdates:
	# 	date = d.get('datetime')
	# 	dates.append(date)
	
	return ids, urls

def error_page(soup):
	if soup.find(class_="error-404 not-found main-page") is not None:
		return True
	return False

# currently must manually update the category in the globals 
# to change desired category
def get_list_of_articles(csv_out):
	csv_name = csv_out if csv_out else "urls_and_ids" + str(datetime.datetime.now())
	global cur_page
	# get_user_params()
	make_readme(csv_name)
	for c in categories:
		print("getting category: " + c + "\n")
		cur_page = 1
		cont = True
		while(cont):
			# 5 second delay between requests to be a good citizen
			time.sleep(5)
			archive_url = base_url + "/" + c + "/page/" + str(cur_page)
			soup = get_soup(archive_url, str(cur_page))
			if (error_page(soup)):
				cont = False
			ids, urls = get_ids(soup)
			write_to_csv(ids, urls, csv_name)
			for u in urls:
				try:
					u.index("2017") 
				except:
					cont = False
			cur_page = cur_page + 1
	print "That's all, folks"

#######################################################

# These functions will generate the article data csv
# [tags, sections, author, date, text]

# Article Text
# 	<div class="pf-content">
# All article tags as provided by berkeleyside
# 	<meta property="article:tag" content="Berkeley elections" />
# Article Sections
#   <meta property="article:section" content="Downtown"/>

# images?  
#######################################################


def write_article_to_csv(data, writer):
	try:
		writer.writerow([data[0]] + [data[1]] + [data[2]] + [data[3]] + [data[4]] + [data[5]] + [data[6]] + [data[7]])
	except:
		print("article writing ERROR")
	print("done.")

def get_text(soup):
	return unidecode(soup.find(class_="pf-content").text)

def get_tags(soup):
	tags = []
	for t in soup.find_all(property = "article:tag"):
		tags.append(t.get("content"))
	return tags

def get_sections(soup):
	sections = []
	for s in soup.find_all(property = "article:section"):
		sections.append(s.get("content"))
	return sections

def get_author(soup):
	return unidecode(soup.find(class_="author vcard").text)

def get_date(soup):
	return soup.find(property="article:published_time").get('content')

def get_title(soup):
	return unidecode(soup.find(class_="entry-title").text)

def process_article(_id, article_url, writer):
	soup = get_soup(article_url, _id + "\n") 
	data = [_id, article_url, get_title(soup), get_tags(soup), get_sections(soup), get_author(soup), get_date(soup), get_text(soup)]
	write_article_to_csv(data, writer)

def process_id(article_id, restart, found):
	if found:
		return True
	if article_id == restart:
		return True
	else:
		return False


def already_seen(_id):
	 global seen_id_list
	 return _id in seen_id_list


def get_data_for_articles(incsv, restart, csv_out):
	global seen_id_list

	make_readme(csv_out)
	with open(csv_out, 'a') as f_out:
		writer = csv.writer(f_out)
		with open(incsv, 'r+') as f_in:
			reader = csv.reader(f_in)
			if restart is '':
				for row in reader:
					if not already_seen(row[0]):
						process_article(row[0], row[1], writer)
						time.sleep(5)
						seen_id_list.append(row[0])

			else: 
				found_restart = False
				for row in reader:
					if not already_seen(row[0]):
						found_restart = process_id(row[0], restart, found_restart)
						if found_restart:
							process_article(row[0], row[1], writer)
							time.sleep(5)
						else:
							print "skipping already processed article"
						seen_id_list.append(row[0])


#######################################################

def main():
	incsv, csv_out, headers, restart = get_args()
	if not incsv:
		get_list_of_articles(csv_out)
	else:
		get_data_for_articles(incsv, restart, csv_out)


main()