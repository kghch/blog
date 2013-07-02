#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Entry Service
version 1.0
history:
2013-6-19    dylanninin@gmail.com    init
"""

import os
import codecs
import re
import datetime
import random
import markdown
from config import blogconfig as config
from tool import Extract
from model import Models

extract = Extract()


class EntryService:
    
    
    
    def __init__(self):
        self.entries = {}
        self.pages = {}
        self.urls = []
        self.by_tags = {}
        self.by_categories = {}
        self.by_months = {}
        self.models = Models()
        self.types = self.models.types()
        self.params = self.models.params()
        self._init_entries()
        
    def _init_entries(self):
        for root, _, files in os.walk(config.entry_dir):
            for f in files:
                self.add_entry(False, root + '/' + f)
        for root, _, files in os.walk(config.page_dir):
            for f in files:
                self._add_page(root + '/' + f)
        self._init_miscellaneous(self.types.add, self.entries.values())
    
    def add_entry(self, inotified, path):
        entry = self._init_entry(self.types.entry, path)
        if not entry == None:
            self.entries[entry.url] = entry
        if not entry == None and inotified:
            self._init_miscellaneous(self.types.add, [entry])

    def delete_entry(self, path):
        for entry in self.entries.values():
            if path == os.path.abspath(entry.path):
                self.entries.pop(entry.url)
                self._init_miscellaneous(self.types.delete, [entry])

    def _add_page(self, path):
        page = self._init_entry(self.types.page, path)
        if not page == None:
            self.pages[page.url] = page

    def _init_entry(self, entry_type, path):
        url, raw_url, name, date, time, content =  self._init_file(path, entry_type)
        if not url == None:
            entry = self.models.entry(entry_type)
            entry.path = path
            entry.name = name
            entry.url = url
            entry.raw_url = raw_url
            entry.date = date
            entry.time = time
            entry.content = content
            entry.excerpt = extract.auto_summarization(entry)
            entry.html = markdown.markdown(content)
            entry.tags = extract.auto_keyphrase(entry)
            entry.categories = extract.auto_categories(entry)
            return entry
        return None

    def _init_file(self, file_path, entry_type):
        """
        #TODO: FIXME: how to determine the publish time of an entry
        """
        content, nones = None, [None for _ in xrange(6)]
        try:
            content = codecs.open(file_path, mode='r', encoding='utf-8').read()
        except:
            return nones
        if content == None or len(content.strip()) == 0:
            return nones
        date = datetime.datetime.now()
        name, _ = os.path.splitext(os.path.basename(file_path))
        chars = ['_' ,'-', '~']
        pattern = r'\d{4}-\d{1,2}-\d{1,2}'
        match = re.search(pattern, name)
        if match:
            y, m, d = match.group().split('-')
            date = datetime.date(int(y), int(m), int(d))
            name = name[len(match.group()):]
            for c in chars:
                if name.startswith(c):
                    name = name[1:]
        else:
            try:
                stat = os.path.stat(file_path)
                date = datetime.datetime.fromtimestamp(stat.st_mtime)
            except:
                pass
        prefix, url_prefix, raw_prefix = date.strftime(config.url_date_fmt), '', ''
        if entry_type == self.types.entry:
            url_prefix = config.entry_url + '/' + prefix + '/'
            raw_prefix = config.raw_url + '/' + prefix + '/'
        if entry_type == self.types.page:
            url_prefix = '/'
            raw_prefix = config.raw_url + '/'
        time = date.strftime(config.time_fmt)
        date = date.strftime(config.date_fmt)
        url = url_prefix + name + config.url_suffix
        raw_url = raw_prefix + name + config.raw_suffix
        for c in chars:
            name = name.replace(c, ' ')
        return url, raw_url, name, date, time, content

    def _init_miscellaneous(self,init_type, entries):
        for entry in entries:
            self._init_tag(init_type, entry.url, entry.tags)
            self._init_category(init_type, entry.url, entry.categories)
            self._init_monthly_archive(init_type, entry.url)
        self.urls = sorted(self.entries.keys(), reverse=True)
        self._init_params()
        
    def _init_subscribe(self):
        time = None
        if self.urls == []:
            time = datetime.datetime.now().strftime(config.time_fmt)
        else:
            time = self.entries[self.urls[0]].time
        return self.models.subscribe(time)

    def _init_tag(self,init_type, url, tags):
        for tag in tags:
            if tag not in self.by_tags:
                if init_type == self.types.add:
                    self.by_tags[tag] = self.models.tag(tag, url)
                if init_type == self.types.delete:
                    pass
            else:
                if init_type == self.types.add:
                    self.by_tags[tag].urls.insert(0, url)
                    self.by_tags[tag].count += 1
                if init_type == self.types.delete:
                    self.by_tags[tag].count -= 1
                    self.by_tags[tag].urls.remove(url)
                    if self.by_tags[tag].count == 0:
                        self.by_tags.pop(tag)

    def _init_category(self, init_type, url, categories):
        for category in categories:
            if category not in self.by_categories:
                if init_type == self.types.add:
                    self.by_categories[category] = \
                    self.models.category(category, url)
                if init_type == self.types.delete:
                    pass
            else:
                if init_type == self.types.add:
                    self.by_categories[category].urls.insert(0, url)
                    self.by_categories[category].count += 1
                if init_type == self.types.delete:
                    self.by_categories[category].count -= 1
                    self.by_categories[category].urls.remove(url)
                    if self.by_categories[category].count == 0:
                        self.by_categories.pop(category)

    def _init_monthly_archive(self,init_type, url):
        start = len(config.entry_url) + 1
        end = start + len('/yyyy/mm')
        month = url[start:end]
        if month not in self.by_months:
            if init_type == self.types.add:
                self.by_months[month] = \
                self.models.monthly_archive(self.types.entry, month, url)
            if init_type == self.types.delete:
                pass
        else:
            if init_type == self.types.add:
                self.by_months[month].urls.insert(0, url)
                self.by_months[month].count += 1
            else:
                self.by_months[month].count -= 1
                self.by_months[month].urls.remove(url)
                if self.by_months[month].count == 0:
                    self.by_months.pop(month)

    def _init_params(self):
        self.params.subscribe = self._init_subscribe()
        self.params.primary.tags = self._init_tags_widget()
        self.params.primary.recently_entries = self._init_recently_entries_widget()
        self.params.secondary.categories = self._init_categories_widget()
        self.params.secondary.calendar = self._init_calendar_widget()
        self.params.secondary.archive = self._init_archive_widget()

    def _init_related_entries(self, url):
        """
            #TODO: FIXME: related entries
        """
        entries = None
        indexes = [random.randint(0, len(self.urls) - 1) for _ in range(0, 10)]
        indexes = set(indexes)
        if len(indexes) > 1:
            urls = [self.urls[index] for index in indexes]
            entries = [self.entries.get(url) for url in sorted(urls, reverse=True)]
        return entries

    def _init_abouts_widget(self, about_types=[], url=None):
        abouts = []
        for about_type in about_types:
            about = self.models.about(about_type)
            if about_type == self.types.entry and not url == None:
                try:
                    i = self.urls.index(url)
                    p, n = i + 1, i - 1
                except:
                    p, n = 999999999, -1
                if p < len(self.urls):
                    url = self.urls[p]
                    about.prev_url = url
                    about.prev_name = self.entries[url].name
                if n >= 0:
                    url = self.urls[n]
                    about.next_url = url
                    about.next_name = self.entries[url].name
            if about_type == self.types.archive:
                about.prev_url = '/'
                about.prev_name = 'main index'
            if about_type == self.types.blog:
                about.prev_url = '/'
                about.prev_name = 'main  index'
                about.next_url = config.archive_url
                about.next_name = 'archives'
            abouts.append(about)
        return abouts

    def _init_tags_widget(self):
        """
        #TODO: FIXME: calculate tags' rank
        """
        tags = sorted(self.by_tags.values(), key=lambda v:v.count, reverse=True)
        ranks = config.ranks
        div, mod = divmod(len(tags), ranks)
        if div == 0:
            ranks = mod
            div = 1
        for r in range(ranks):
            start = r * div
            end = start + div
            for tag in tags[start:end]:
                tag.rank = r + 1
        return tags

    def _init_recently_entries_widget(self):
        return [self.entries[url] for url in self.urls[:config.recently]]

    def _init_calendar_widget(self):
        date = datetime.datetime.today().strftime(config.date_fmt)
        if len(self.urls)> 0:
            date = self.entries[self.urls[0]].date
        calendar = self.models.calendar(date)
        ym = calendar.month
        y, m = ym.split('-')
        for url in self.urls:
            _, _, _, _, d, _ = url.split('/')
            prefix = config.entry_url + '/' +  y + '/' + m + '/' + d
            d = int(d)
            if url.startswith(prefix):
                calendar.counts[d] += 1
                if calendar.counts[d] > 1:
                    start = len(config.entry_url)
                    end = start + len('/yyyy/mm/dd')
                    calendar.urls[d] = config.archive_url + url[start:end]
                else:
                    calendar.urls[d] = url
            else:
                break
        return calendar

    def _init_categories_widget(self):
        return self.by_categories.values()

    def _init_archive_widget(self):
        return sorted(self.by_months.values(), key=lambda m:m.url, reverse=True)

    def _find_by_query(self, query, start, limit):
        queries = [q.lower() for q  in query.split(' ')]
        urls = []
        for query in queries:
            for entry in self.entries.values():
                try:
                    entry.content.index(query)
                    urls.append(entry.url)
                except:
                    pass
        return self._find_by_page(sorted(urls), start, limit)

    def _find_by_page(self, urls, start, limit):
        if urls == None or start < 0 or limit <= 0:
            return [], 0
        total = len(urls)
        urls = sorted(urls, reverse=True)
        s, e = (start - 1) * limit, start * limit
        if s > total or s < 0:
            return [], 0
        return [self.entries[url] for url in urls[s:e]], total

    def _paginate(self, pager_type, value, total, start, limit):
        if limit <= 0:
            return self.models.pager(pager_type, value, total, 0, start, limit)
        pages, mod = divmod(total,limit)
        if mod > 0:
            pages += 1
        return self.models.pager(pager_type, value, total, pages, start, limit)

    def find_by_url(self, entry_type, url):
        entry = None
        if entry_type == self.types.entry:
            entry = self.entries.get(url)
            self.params.primary.abouts = self._init_abouts_widget([self.types.entry, self.types.blog], url)
        if entry_type == self.types.page:
            entry = self.pages.get(url)
            self.params.primary.abouts = self._init_abouts_widget([self.types.blog], url)
        if entry == None:
            self.params.primary.abouts = self._init_abouts_widget([self.types.blog])
        self.params.entry = entry
        self.params.entries = self._init_related_entries(url)
        self.params.error = self.models.error(url=url)
        return self.params

    def find_raw(self, raw_url):
        page_url = raw_url.replace(config.raw_url, '').replace(config.raw_suffix, config.url_suffix)
        page = self.find_by_url(self.types.page, page_url).entry
        if not page== None and page.raw_url == raw_url:
            return page.content
        entry_url = raw_url.replace(config.raw_url, config.entry_url).replace(config.raw_suffix, config.url_suffix)
        entry = self.find_by_url(self.types.entry, entry_url).entry
        if not entry == None and entry.raw_url == raw_url:
            return entry.content
        return None

    def archive(self, archive_type, url, start=1, limit=999999999):
        self.params.error = self.models.error(url=url)

        if archive_type == self.types.raw:
            url = url.replace(config.raw_url,config.archive_url)

        entries, count, = [], 0
        archive_url = url.replace(config.archive_url, '').strip('/')
        prefix =  url.replace(config.archive_url, config.entry_url)
        pattern = r'\d{4}/\d{2}/\d{2}|\d{4}/\d{2}|\d{4}'
        match = re.search(pattern, archive_url)
        if match and match.group() == archive_url or archive_url == '':
            urls = [url for url in self.urls if url.startswith(prefix)]
            entries, _  =  self._find_by_page(urls, start, limit)
            count = len(entries)
        else:
            entries = None
        if archive_url == '':
            archive_url = self.types.all

        self.params.entries = entries
        self.params.archive = self.models.archive(archive_type, url, archive_url, url, count)
        self.params.primary.abouts = self._init_abouts_widget([self.types.archive])
        return self.params

    def search(self, search_type, url, value='', start=config.start, limit=config.limit):
        entries, total = None, 0
        if  search_type == self.types.query:
            entries, total = self._find_by_query(value, start, limit)
        if search_type == self.types.tag:
            if self.by_tags.get(value) == None:
                entries = None
            else:
                entries, total = self._find_by_page(self.by_tags.get(value).urls, start, limit)
        if search_type == self.types.category:
            if self.by_categories.get(value) == None:
                entries = None
            else:
                entries, total = self._find_by_page(self.by_categories.get(value).urls, start, limit)
        self.params.primary.abouts = self._init_abouts_widget([self.types.blog])
        if search_type == self.types.index:
            entries, total = self._find_by_page(self.urls, start, limit)
            self.params.primary.abouts = self._init_abouts_widget([])
        self.params.error = self.models.error(url=url)
        self.params.entries = entries
        self.params.search = self.models.search(search_type, value, total)
        self.params.pager = self._paginate(search_type, value, total, start, limit)
        return self.params

    def error(self, url):
        self.params.error = self.models.error(url=url)
        self.params.primary.abouts = self._init_abouts_widget([self.types.blog])
        return self.params

if __name__ == '__main__':
    import doctest
    doctest.testmod()