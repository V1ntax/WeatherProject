from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import sqlite3
import re

conn = sqlite3.connect('weatherDB.sqlite')
cur = conn.cursor()

# Creating SQL Tables
cur.executescript('''

CREATE TABLE IF NOT EXISTS AdditWeather (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
    falls TEXT,
    wet TEXT,
    wind TEXT
);

CREATE TABLE IF NOT EXISTS Weather (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
    temp TEXT,
    typeWeather TEXT,
    additWeather_id INTEGER
);

CREATE TABLE IF NOT EXISTS Main (
    id INTEGER NOT NULL PRIMARY KEY,
    location TEXT,
    time TEXT,
    locMap TEXT,
    weather_id INTEGER
);
''')

# Son Firainsoslko
query = input('\nIn which location do you want to know the weather? ')
url = f'https://www.google.com/search?q=weather+{query}'

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
driver.get(url)
soup = BeautifulSoup(driver.page_source, "html.parser")

# print(soup.prettify(), '\n--------------------------------------------------------')

def findAllValues(soupDef):
    global temp, loc, time, TWeather, falls, wet, wind
    # Finding all results
    temp = str(soupDef.find(class_='wob_t q8U8x').text) + '°C'
    time = str(soupDef.find('div', class_='wob_dts').text)
    TWeather = str(soupDef.find('div', class_='wob_dcp').span.text)
    loc = str(soupDef.find('span', class_='BBwThe').text)

    # --- Additional parms (falls, wet, wind) ---
    divAdditions = soupDef.find('div', class_='wtsRwe')
    falls = str(divAdditions.find('span', id='wob_pp').text)
    wet = str(divAdditions.find('span', id='wob_hm').text)
    wind = str(divAdditions.find('span', id='wob_ws').text)

# ----------- SQL : -------------
def sqlCode():
    cur.execute('''INSERT OR IGNORE INTO AdditWeather (falls, wet, wind)
        VALUES ( ?, ?, ?)''', (falls, wet, wind))
    cur.execute('''SELECT id FROM AdditWeather 
            WHERE falls = ? AND wet = ? AND wind = ?''', (falls, wet, wind))
    additWeather_id = cur.fetchone()[0]

    cur.execute('''INSERT OR IGNORE INTO Weather (temp, typeWeather, additWeather_id)
        VALUES ( ?, ?, ?)''', (temp, TWeather, additWeather_id))
    cur.execute('''SELECT id FROM Weather
            WHERE temp = ? AND typeWeather = ? AND additWeather_id = ?''', (temp, TWeather, additWeather_id))
    weather_id = cur.fetchone()[0]

    cur.execute('''INSERT OR REPLACE INTO Main
            (location, time, locMap, weather_id)
            VALUES ( ?, ?, ?, ? )''',
            (loc, time, locMap, weather_id))


locMap = str
# Try/Except Error checking
try:
    if soup.find('a', class_='gL9Hy') is None:

        # --- Finding GOOGLE MAP LINK of Location ---
        # and checking if Query has 2 or more words and correct Url by adding '+' between words
        a = query.split()
        if len(a) > 1:
            query = f"{a[0]}"
            a = a[1:]
            for i in range(len(a)):
                query = query + f"+{a[i]}"
        locMap = f'https://maps.google.com/maps?q={query}'

        # Finding today info and next 7 days
        numOfXpath = 1
        while numOfXpath <= 8:
            xpath = f'//*[@id="wob_dp"]/div[{numOfXpath}]'
            myElem = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.XPATH, xpath)))
            myElem.click()

            soup = BeautifulSoup(driver.page_source, "html.parser")
            findAllValues(soup)

            print('\nDay :', time)
            print('Temperature :', temp)
            print('Type of weather :', TWeather)
            print('Опади, вологість, вітер :', falls, ',', wet, ',', wind)

            numOfXpath = numOfXpath + 1

            #SQL :
            sqlCode()

        conn.commit()

        print('\nLocation :', loc)
        print('Google maps link -', locMap, '\n')

    else:
        # Query written wrong, finding correct link & correct query
        spanCorrection = soup.find('a', class_='gL9Hy')
        correctedUrl = ('https://www.google.com' + spanCorrection['href'])
        correctedQuery = re.findall(r"[\w']+", spanCorrection['href'])

        # Checking if Query has 2 or more words, then correct Url by adding '+' between words
        startQ = correctedQuery.index('weather')
        endQ = correctedQuery.index('spell')
        correctedQuery = "+".join(correctedQuery[startQ+1:endQ])

        driver.get(correctedUrl)
        soupCor = BeautifulSoup(driver.page_source, "html.parser")
        # print(soupCor.prettify())

        # --- Finding GOOGLE MAP LINK of Location ---
        locMap = f'https://maps.google.com/maps?q={correctedQuery}'

        # Finding today info and next 7 days
        numOfXpath = 1
        while numOfXpath <= 8:
            xpath = f'//*[@id="wob_dp"]/div[{numOfXpath}]'
            myElem = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.XPATH, xpath)))
            myElem.click()

            soupCor = BeautifulSoup(driver.page_source, "html.parser")
            findAllValues(soupCor)

            print('\nDay :', time)
            print('Temperature :', temp)
            print('Type of weather :', TWeather)
            print('Опади, вологість, вітер :', falls, ',' , wet, ',' , wind)

            numOfXpath = numOfXpath + 1

            #SQL :
            sqlCode()

        conn.commit()

        print('\nLocation :', loc)
        print('Google maps link -', locMap, '\n')
except:
    print('\n\tLocation is written wrong! Try again.')
    exit()

# Info from SQL tables
print('\nFrom SQL tables: \n')
sqlstr =  'SELECT Main.location, Main.time, Weather.temp, Weather.typeWeather, AdditWeather.falls, AdditWeather.wet, AdditWeather.wind, Main.locMap FROM Main JOIN Weather JOIN AdditWeather ON Main.weather_id = Weather.id and Weather.additWeather_id = AdditWeather.id'

count = 0
for row in cur.execute(sqlstr):
    print(f'{row[0]} , {row[1]} , {row[2]} , {row[3]} , {row[4]} (опади), {row[5]} (вологість), {row[6]} (вітер)')
    count = count + 1
    if count % 8 == 0 and count != 0:
        print('Map link :', row[7])
        print('\n')

driver.close()

# Reset tables (Drop Tables)
reset = input('Would you like to reset DataBase? (yes or no) ')
if len(reset) < 1: exit()
elif reset not in ['yes', 'no', 'Yes', 'No', 'YES', 'NO']:
    print('The answer is written wrong!')
    exit()

if reset in ['yes', 'Yes', 'YES']:
    cur.executescript('''
    DROP TABLE IF EXISTS Main;
    DROP TABLE IF EXISTS Weather;
    DROP TABLE IF EXISTS AdditWeather;
    ''')

conn.close()