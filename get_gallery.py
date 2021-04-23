import logging
import requests
import re
import sys
import argparse
import os

from bs4 import BeautifulSoup, UnicodeDammit


class gallery_retrieval(object):

    def __init__(self, url, outputFolder):

        # What url is this:
        url_type = self.what_url_is_this(url)
        self.base_url = url.rsplit('/', 3)[0]

        # Get things done:
        first_page_soup = self.fetch_url(url)
        self.gallery_name = self.get_gallery_name(first_page_soup)
        self.gallery_folder = os.path.join(outputFolder, self.gallery_name)

        # Based on the url type we need to get the gallery url:
        self.gallery_url = url if url_type == 'gallery' else self.get_gallery_url(
            first_page_soup)

        logging.info(f'URL type: {url_type}')
        logging.info(f'Base URL: {self.base_url}')
        logging.info(f'Gallery name: {self.gallery_name}')
        logging.info(f'Gallery URL: {self.gallery_url}')

        # Initialize empty list for image urls:
        self.image_urls = []

        self.get_image_urls_from_gallery(self.gallery_url)
        logging.info(
            f'Number of images found in the gallery: {len(self.image_urls)}')

        # Create gallery:
        try:
            os.makedirs(self.gallery_folder, exist_ok=True)
        except OSError:
            logging.error("Creation of the directory %s failed" %
                          self.gallery_folder)
        else:
            logging.info("Successfully created the directory %s" %
                         self.gallery_folder)

    @staticmethod
    def get_gallery_url(soup):
        return [x.get('href') for x in soup.findAll('a') if '/gallery.php?' in x.get('href')][0]

    @staticmethod
    def what_url_is_this(url):
        '''
        Classifying urls to 'gallery', 'photo' or 'other'
        '''

        if re.match('https://www\.image.+pictures/\d+/.+', url):
            return 'gallery'
        elif re.match('https://www\.image.+photo/\d+', url):
            return 'photo'
        else:
            return 'other'

    @staticmethod
    def fetch_url(url):
        '''
        fethc the provided url and returns a soup object
        '''
        response = requests.get(url)

        # Returned html document:
        html = response.text

        # Html encoded into utf8:
        uhtml = UnicodeDammit(html)

        # Creating soup:
        soup = BeautifulSoup(uhtml.unicode_markup, features="html.parser")

        return soup

    @staticmethod
    def get_gallery_name(soup):
        '''
        From a soup object, parsed gallery name is returned.
        Not 100% perfect: in theory it could fail, but haven't
        seen any galleries breaking.
        '''

        # Finding relevant td-s:
        tds = [td for td in soup.findAll(
            'td') if 'Uploaded' in td.text and not td.find('td')]
        title = ''

        # This might fail, but will test if something has been found:
        for td in tds:
            try:
                title += [x for x in tds[0].text.split('\n') if x != ''][0]
            except ValueError:
                continue

        if title == '':
            title = None
        else:
            title = title.replace(' ', '_')

        return title

    def get_image_urls_from_gallery(self, gallery_url):
        """
        Based on a soup of a gellery page, we get a parsable url:
        """

        # Fetch gallery:
        soup = self.fetch_url(gallery_url)

        # Collect all urls on the first page:
        for a in soup.findAll('a'):
            if a.find('img') and a.get('href').startswith('/photo'):

                # Adding completed URL to the list:
                self.image_urls.append(f"{self.base_url}{a.get('href')}")

        # Is there a next page:
        next_page_urls = [a.get('href') for a in soup.findAll(
            'a') if a.text == ':: next ::']

        if len(next_page_urls) > 0:
            next_page_url = f'{self.gallery_url}{next_page_urls[0]}'
            self.get_image_urls_from_gallery(next_page_url)

    def save_images(self):
        '''
        This function downloads all image pages and saves relevant metadata + saves photo
        '''
        logging.info('Fetching images...')
        for image_url in self.image_urls:

            # Fetch data:
            soup = self.fetch_url(image_url)

            # Extract image id:
            # image_id = re.search('\/photo\/(\d+)', image_url).group(1)

            # Extract image name:
            image_name = soup.find('title').text.split('rn Pic ')[0][:-3]

            # Extract image url:
            image_links = [img.get('src') for img in soup.findAll(
                'img') if img.get('src') and '/images/full' in img.get('src')]
            if len(image_links) == 0:
                logging.warn(
                    f'Failed to find image url for this page: {image_url}')
                continue

            # Save image
            image_data = requests.get(image_links[0])
            with open(f'{self.gallery_folder}/{image_name}', 'wb') as image_file:
                image_file.write(image_data.content)


def main():

    # Parsing argument:
    parser = argparse.ArgumentParser(
        description='This script retrieves image galleries based on the provided URL.')
    parser.add_argument(
        '--url', help='Input URL pointing to a gallery or a photo', type=str, required=True)
    parser.add_argument(
        '--outputFolder', help='Folder in which the gallery will be saved.', type=str, required=False)
    args = parser.parse_args()

    url = args.url

    # If no output folder is specified, the current directory is used:
    if args.outputFolder:
        outputFolder = args.outputFolder
    else:
        outputFolder = os.getcwd()

    # Set up logging:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(module)s - %(funcName)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    logging.StreamHandler(sys.stderr)

    # Call the downloader:
    gallery_downloader = gallery_retrieval(url, outputFolder)
    gallery_downloader.save_images()


if __name__ == '__main__':
    main()
