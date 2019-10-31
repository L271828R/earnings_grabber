import time
import selenium
import sys
import random
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from datetime import datetime
from pymongo import MongoClient
from datetime import datetime
from tickers import tickers


# 52week range
# PE Ratio
# MC
# price
# change
# latest headline
# sector 
# industry
# website
# employees
# data-test="EARNINGS_DATE-value"


class Page(object):
    def __init__(self, driver, conf):
        self.driver = driver
        self.goto_template_main = "https://finance.yahoo.com/quote/__TICKER__"
        self.goto_template_profile = "https://finance.yahoo.com/quote/__TICKER__/profile?p=__TICKER__"

    def goto_main(self, ticker):
        url = self.goto_template_main.replace("__TICKER__", ticker)
        self.driver.get(url)
        time.sleep(1)

    def get_attribute(self, attr_value):
        list_of_tds = self.driver.find_elements_by_tag_name('td')
        for count, el in enumerate(list_of_tds):
            attr = el.get_attribute('data-test')
            if attr is not None and attr_value in attr:
                return el.text
        return None


    def get_category(self, category, spans):
        for count, span in enumerate(spans):
            if category in span.text:
                return spans[count + 1].text

    def get_url(self, hrefs):
        for href in hrefs:
            if 'http' in href.text:
                return href.text
    
    


    def goto_profile(self, ticker):
        url = self.goto_template_profile.replace('__TICKER__', ticker)
        self.driver.get(url)
        time.sleep(1)
        



    def get_industry_info(self, ticker):
        self.goto_profile(ticker)
        result = {
            'address': "",
            'sector': "",
            'industry': "",
            'employees': "",
            'company-name': ""
        }

        try:
            container = self.driver.find_element_by_class_name('asset-profile-container')
            header = self.driver.find_element_by_id('quote-header-info')
            company_name = header.find_elements_by_tag_name('h1')[0].text
            spans = container.find_elements_by_tag_name('span')
            ps = container.find_elements_by_tag_name('p')[0].text.split('\n')[:-2]
            address = " ".join(ps)
            sector = self.get_category('Sector', spans)
            industry = self.get_category('Industry', spans)
            employees = self.get_category('Full Time Employees', spans)
            result = {
                'address': address,
                'sector': sector,
                'industry': industry,
                'employees': employees,
                'company-name': company_name
            }
        except selenium.common.exceptions.NoSuchElementException:
            pass
        
        return result


    def get_earnings_pe_market_cap(self, ticker):
        self.goto_main(ticker)
        time.sleep(3)
        earnings_date = self.get_attribute('EARNINGS_DATE-value')
        earnings_date_iso = None
        print('raw=', earnings_date)

        if earnings_date is not None and '-' in earnings_date:
            earnings_date = earnings_date.split('-')[0].strip()
            print('in split')
            print('process=', earnings_date)

        if earnings_date is not None and 'N/A' not in earnings_date:
            earnings_date_iso = datetime.strptime(earnings_date, "%b %d, %Y")
            earnings_date = earnings_date_iso.strftime("%Y-%m-%d")
        else:
            earnings_date = ''
        pe_ratio = self.get_attribute('PE_RATIO-value')
        market_cap = self.get_attribute('MARKET_CAP-value')
        return {'ticker': ticker,
                'earnings-date-iso': earnings_date_iso,
                'earnings-date': earnings_date,
                'pe-ratio': pe_ratio,
                'market-cap': market_cap
                }

def create_driver(conf):
    chrome_options = Options()
    if conf["headless"]:
        chrome_options.add_argument("--headless")
    return  webdriver.Chrome(".//chromedriver", chrome_options=chrome_options)

def is_saved(conn, ticker):
    return False
    db = conn.database
    collection = db.basic_data
    cursor = collection.find({
            'ticker': ticker,
            'saved_on': datetime.now().strftime("%Y-%m-%d")
        })
    if cursor.count() == 0:
        return False
    else:
        return True
    return False



def save_data(conn, data):
    db = conn.database
    collection = db.basic_data
    collection.remove({'ticker':data['ticker']})
    collection.insert_one(data)






if __name__ == '__main__':
    conf = {"headless": True}
    conn = None
    try: 
        conn = MongoClient() 
        print("Connected successfully!!!") 
    except:   
        print("Could not connect to MongoDB") 
    driver = create_driver(conf)
    print(sys.argv)
    page = Page(driver, conf)
    if len(sys.argv) > 1:
        ticker = sys.argv[1]
        page.goto_main(ticker)
        data = page.get_earnings_pe_market_cap(ticker)
        save_data(conn, data)
        print('saved values for ', ticker)

    else:
        for count, ticker in enumerate(tickers):
            if not is_saved(conn, ticker):
                print(ticker)
                page.goto_main(ticker)
                data = page.get_earnings_pe_market_cap(ticker)
                data2 = page.get_industry_info(ticker)
                data_to_save = {}
                data_to_save.update(data)
                data_to_save.update(data2)
                save_data(conn, data_to_save)
                print(count, 'saved values for', ticker)
    driver.close()
    driver.quit()
    print('done!')


