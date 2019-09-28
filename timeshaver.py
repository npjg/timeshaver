from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from dataclasses import dataclass
import pandas as pd
import numpy as np

***REMOVED***


class AdpError(Exception):
    """Base exception for all TimeSaver exceptions.
    :param str message: a description of the exception
    """
    message = None

    def __init__(self, message=None):
        self.message = message or self.message
        super().__init__(self.message)
        
    
class AuthenticationError(AdpError):
    """Exception raised when an unauthorized access attempt has been made."""
    message = "The user attempted an unauthorized access to a resource."


@dataclass
class Credentials:
    uid: str
    passwd: str
    
class TimeSaver:
    def __init__(self):
        # Create a headless browser
        options = Options()
        self.driver = webdriver.Firefox(options=options)
        self.driver.get(TIMESAVER_FRONTPAGE)
        self.credentials = None
        self._sites = None
        self._timetable = None

    def __del__(self):
        # Delete the headless browser
        self.driver.close()

    def authenticate(self):
        """Login to TimeSaver with the provided credentials."""
        uid_field = self.driver.find_element_by_id("username")
        passwd_field = self.driver.find_element_by_id("password")

        uid_field.send_keys(self.credentials.uid)
        passwd_field.send_keys(self.credentials.passwd)

        self.driver.find_element_by_id("bttSubmit").click()
        if not self.is_authenticated():
            raise AuthenticationError

    def logoff(self):
        """Log out of TimeSaver."""
        self.driver.find_element_by_id("logoffLinkImage").click()

    @property
    def last_login(self):
        """Get the last successgul login time."""
        info = self.driver.find_element_by_xpath("//*[contains(text(), 'Last successful login')]")
        return info.text

    @property
    def approval_status(self):
        """Get approval status for the current period,
or return an empty string if no approval status can be found."""
        info = self.driver.find_element_by_id("spanTimePeriodApprovalStatus")
        return info.text

    @property
    def sites(self):
        if self._sites is None:
            self._sites = Select(self.driver.find_element_by_id("FRMTimestampSite"))
        return self._sites

    @property
    def site(self):
        """Return the currently selected work site."""
        return self.sites.all_selected_options[0].text

    @site.setter
    def site(self, idx):
        """Select a work site by index."""
        self.sites.select_by_index(idx)

    @property
    def sites_text(self):
        """Describe all available work sites."""
        return [option.text for option in self.sites.options]


    @property
    def timetable(self):
        if self._timetable is None:
            self.driver.find_element_by_id("anchorFolderTabs2").click()
            raw = self.driver.find_elements_by_xpath("//*[contains(@id, 'TimeEntriesRepeater')]")
            header = self.driver.find_elements_by_xpath("//*[@id='TimeEntriesHeader']/tr/th")
            
            columns = [
                column.text
                for column in header
            ]

            data = np.array([
                punch for punch in
                  [[element.text
                   for element in row.find_elements_by_xpath('td')]
                for row in raw]
                 if punch
            ])

            self._timetable = pd.DataFrame(data=data, columns=columns)

        return self._timetable
            
    def is_authenticated(self):
        """Check that we have successfully authenticated."""
        try:
            header = self.driver.find_elements_by_css_selector("ADPUI-HeaderTitle")
        except:
            raise AuthenticationError

        raise NotImplementedError

    
        
