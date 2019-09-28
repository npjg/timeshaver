from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options

***REMOVED***


class TimeSaver():
    def __init__(self):
        # Create a headless browser
        options = Options()
        self.driver = webdriver.Firefox(options=options)
        self.driver.get(TIMESAVER_FRONTPAGE)


    def __del__(self):
        # Delete the headless browser
        self.driver.close()

    def login(self, uid, passwd, role="Employee"):
        """Login to TimeSaver with the provided credentials."""
        uid_field = self.driver.find_element_by_id("username")
        passwd_field = self.driver.find_element_by_id("password")

        uid_field.send_keys(uid)
        passwd_field.send_keys(passwd)

        self.driver.find_element_by_id("bttSubmit").click()
        self.verify()
 
