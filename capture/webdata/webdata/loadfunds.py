import sys
from lxml import etree
import mysql.connector
import datetime

class HTMLPages:
    Server = "http://web.msse.se/"
    URLvalue = 'http://web.msse.se/SKANDIA/vips/ska/all/sv/quickrank?page=1&subtab=all'
    URLrisk = 'http://web.msse.se/SKANDIA/vips/ska/all/sv/quickrank/riskrating?page=1&subtab=all'
    URLfee = 'http://web.msse.se/SKANDIA/vips/ska/all/sv/quickrank/fees?page=1&subtab=all'
    
    def __init__(self):
        self.urlDict = {}
        self._numberOfPages = 0
     
    def getNumberOfPages(self):
        if (self._numberOfPages == 0):
            urlString = self.getPage(HTMLPages.URLvalue).xpath("//li/a[text() = 'Sista']/@href")
            print (str(urlString))
            if (len(urlString) > 0):
                self._numberOfPages = int(urlString[0].split("page=")[1].split("&")[0])
        return self._numberOfPages
    
    def getUrlByNumber(self,url,n):
        return url.replace("page=1","page=" + str(n))
    
    def getPageByNumber(self, url, n):
        return  self.getPage(self.getUrlByNumber(url, n))
    
    def getPage(self,key):
        if (key not in self.urlDict):   
            try: 
                parser = etree.HTMLParser()
                result = etree.parse(key, parser).getroot()
                self.urlDict[key] = result
            except Exception as e: 
                print ("Exception at getPage " + str(e))
                raise e
                    
        return self.urlDict[key]
    
    def listSymbolsByNumber(self,n):
        ids = self.getPageByNumber(HTMLPages.URLvalue, n).xpath("//tr/@id")
        symbols = []
        for s in ids:
            symbols.append(s.replace("row-","").replace("-1",""))
        return symbols
            
    
    def findTableByNumber(self,url,n,symbol):
        url = self.getUrlByNumber(url,n)
        return self.findTable(url,symbol) 
         
    def findTable(self,url,symbol):    
        tab = self.getPage(url).xpath("//tr[@id = $v]/td", v = "row-" + symbol + "-1")
        return tab   
       
class ScandiaFund:
     
    def __init__(self,htmlPages,pageNumber,symbol):
        self.name = ""
        self.value = ""
        self.currency = ""
        self.valueDate = ""
        self.riskSTD = ""
        self.feeMaintenance =""
        self.feeAnnual =""
        self.feeBuy =""
        self.feeSell =""
        self.symbol = symbol
        self.pageNumber = pageNumber
        self.htmlPages = htmlPages
        self.detailURL1 = ""
        self.detailURL2 = ""

        self.find()
        
    def find(self):
        
        # Value 
        table = self.htmlPages.findTableByNumber(HTMLPages.URLvalue,self.pageNumber,self.symbol)         
        self.name = table[0].attrib['title']
        self.value = self.assertNumber( table[1].text)
        self.currency = table[2].text.strip()
        date = table[3].text.strip().split("/")
        self.valueDate = str(datetime.datetime.now().year)
        if (int(date[1]) < 10):
            self.valueDate += "0"
        self.valueDate += date[1]
        if (int(date[0]) < 10):
            self.valueDate += "0"
        self.valueDate += date[0]
        if (len(table[8].xpath("./a/@href")) >0): 
            self.detailURL1 =   table[8].xpath("./a/@href")[0] 
            print("1 "+ self.detailURL1)
        if (len(table[0].xpath("./span/a/@href")) > 0):
            self.detailURL2 = table[0].xpath("./span/a/@href")[0]
            print ("2 "+ str(self.detailURL2))
        
        # risk
        table = self.htmlPages.findTableByNumber(HTMLPages.URLrisk,self.pageNumber,self.symbol)
        self.riskSTD = self.assertNumber(table[6].text.strip())
        
        # fee
        table = self.htmlPages.findTableByNumber(HTMLPages.URLfee,self.pageNumber,self.symbol)             
        self.feeMaintenance = self.assertNumber(table[1].text.strip())
        self.feeAnnual =  self.assertNumber(table[2].text.strip())
        self.feeBuy = self.assertNumber(table[3].text.strip())
        self.feeSell = self.assertNumber(table[4].text.strip())
        
    def assertNumber(self,s):
        ss = s.strip().replace(",",".")
        sss = ""
        for i in range(0,len(ss)):
            if (ord(ss[i]) != 160):
                sss += ss[i]      
        try:
            float(sss)
            return sss
        except ValueError:
            if (len(sss) > 1):
                print("VALUE ERROR " + sss + ">" + str(ord(sss[1])) ) 
            return 0.0
    
    def dump(self):
        h = vars(self)
        keys = vars(self).keys()
        for k in keys:
            print (k, '=' , h[k])
            
     
pages = HTMLPages()    
try:
    if ( pages.getNumberOfPages() == 0 ):
        print ("No pages! Server or internet connection may be down!")  
        sys.exit(0)
except Exception as e:
    print("No pages! Server or internet connection may be down!")
    sys.exit(0)
    
statement1="""INSERT INTO funds (valueDate,symbol,name,value,std,feeAnnual,feeMaintenance,feeBuy,feeSell) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON duplicate key UPDATE value = value"""
statement2="""INSERT INTO fundsStatics (symbol,termsheetURL1,termsheetURL2) VALUES (%s,%s,%s) ON duplicate key UPDATE termsheetURL1 = termsheetURL1, termsheetURL1 = termsheetURL1"""

try:   
    conn = mysql.connector.connect(user='malin', password='katten3',host='192.168.1.2',database='mydb')
except mysql.connector.Error as err:
    print("Exception " + str(err))
    sys.exit(0)

print("Database opened!") 
cursor = conn.cursor()

for n in range(1,int(pages.getNumberOfPages())+1):
    for s in pages.listSymbolsByNumber(n):
        print ("Getting page# " + str(n) + " symbol " + s)
        fund = ScandiaFund(pages,n,s)
        #fund.dump()
        try:     
            cursor.execute (statement1, (fund.valueDate,
                                   fund.symbol,
                                   fund.name,
                                   fund.value,  
                                   fund.riskSTD,
                                   fund.feeAnnual,
                                   fund.feeMaintenance,
                                   fund.feeBuy,
                                   fund.feeSell))
            conn.commit()
        except Exception as err:
            print("Exception statement1" + str(err) )
            conn.rollback()
            conn.close()
            sys.exit(0) 
            
        try:     
            print (fund.symbol)
            print (fund.detailURL1)
            print (fund.detailURL2)
            cursor.execute (statement2,(fund.symbol,
                                        str(fund.detailURL1),
                                        str(fund.detailURL2)
                                        ))
            conn.commit()
        except Exception as err:
            print("Exception statement2 " + str(err) )
            conn.rollback()      
            conn.close()
            sys.exit(0)    

conn.close()
print("Database closed!")   






    