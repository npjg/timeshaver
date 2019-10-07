from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.select import Select
from cached_property import cached_property
from dataclasses import dataclass
import pandas as pd
import numpy as np
from enum import Enum
import datetime as dt


class AdpError(Exception):
    """Base exception for all TimeSaver exceptions.
    :param str message: a description of the exception
    """
    message = None

    def __init__(self, message=None):
        self.message = message or self.message
        super().__init__(self.message)

@dataclass
class Credentials:
    uid: str
    passwd: str


class Periods(Enum):
    Current = "Current Period"
    Previous = "Previous Period"
    Next = "Next Period"
    Custom = "Date Range"


class TimeSaver:
    def __init__(self, version, key, headless=True):
        # Create a headless browser
        options = Options()
        options.headless = headless
        self.driver = webdriver.Firefox(options=options)
        self.service = ["https://timesaver.adphc.com",
                        version,
                        key,
                        'TS',
                        'login.php']

        self.driver.implicitly_wait(2)
        self.driver.get(self.base_url)

        self.credentials = None

    def __del__(self):
        # Log off safely and delete the headless browser
        self.logoff()
        self.driver.close()

    @property
    def base_url(self):
        return  '/'.join(self.service)

    def make_dataframe_from_html(self, table, row_xpath, header):
        """Makes a pandas dataframe from a Selenium HTML object TABLE, with rows
        referenced by ROW_XPATH and columns provided by a list in COLUMNS. If
        TABLE is empty, return an empty DataFrame.
        """

        columns = [
            column.get_attribute("textContent").strip() for column in header 
        ]

        if table:
            data = np.array([
                nonnull for nonnull in
                [[atom.get_attribute("textContent").strip()
                  for atom in row.find_elements_by_xpath(row_xpath)]
                 for row in table]
                if nonnull
            ])

            dataframe = pd.DataFrame(data=data, columns=columns)
        else:
            dataframe = pd.DataFrame()

        return dataframe

    def map_input(self, rules):
        for rule in rules:
            element = self.driver.find_element_by_id(rule[0])
            element.clear()
            element.send_keys(rule[1])

    def authenticate(self):
        """Login to TimeSaver with the provided credentials."""
        elements = [
            ("username", self.credentials.uid),
            ("password", self.credentials.passwd)
        ]

        self.map_input(elements)

        self.driver.find_element_by_id("bttSubmit").click()

    def logoff(self):
        """Log out of TimeSaver."""
        self.driver.find_element_by_id("logoffLinkImage").click()

    @cached_property
    def logoff_selector(self):
        return self.driver.find_element_by_id(
            "FRMLogoffAfterTransactionTimestamp"
        )

    @property
    def logoff_after_transaction(self):
        """Says whether automatic logoff is enabled."""
        return self.logoff_selector.get_property("checked")

    @logoff_after_transaction.setter
    def logoff_after_transaction(self, value):
        "Sets the automatic logoff selector via a boolean."
        if value ^ self.logoff_after_transaction:
            self.logoff_selector.click()

    def punch(self):
        """Submit a new punch."""
        self.driver.find_element_by_id("anchorFolderTabs1").click()
        self.driver.find_element_by_id("bttAddPunch").click()
        self.driver.find_element_by_id("FloatMsgBtn0").click()

    def change_password(self, new_passwd):
        """Submit a password-change request."""
        self.driver.find_element_by_id("bttChangePassword").click()

        elements = [
            ("FRMOldPassword", self.credentials.passwd),
            ("FRMNewPassword", new_passwd),
            ("FRMConfirmPassword", new_passwd)
        ]

        self.map_input(elements)
        self.driver.find_element_by_id("bttOk").click()

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

    @cached_property
    def sites_selector(self):
            # self.driver.find_element_by_id("anchorFolderTabs1").click()
            return Select(self.driver.find_element_by_id("FRMTimestampSite"))

    @cached_property
    def sites(self):
        """Describe all available work sites in an indexed list."""
        return [option.get_attribute("textContent")
                for option in self.sites_selector.options]

    @property
    def site(self):
        """Return the currently selected work site."""
        return self.sites_selector.all_selected_options[0].text

    @site.setter
    def site(self, idx):
        """Select a work site by index."""
        sites = Select(self.driver.find_element_by_id("FRMTimestampSite"))
        sites.select_by_index(idx)


    @cached_property
    def jobcodes(self):
        """Describe all available job codes."""
        table = self.driver.find_elements_by_xpath(
            "//*[contains(@id, 'tr_FRMTimestampDeptPosCombo')]"
        )

        header = self.driver.find_elements_by_xpath(
            "//*[@id='trMultiColumnTitles_FRMTimestampDeptPosCombo']/th/p"
        )

        return self.make_dataframe_from_html(table, '/td/p', header)

    @property
    def jobcode(self):
        """Return the currently selected jobcode."""
        return self.driver.find_element_by_id(
            "FRMTimestampDeptPos"
        ).get_attribute("value")

    @jobcode.setter
    def jobcode(self, idx):
        "Set a jobcode by index."
        self.driver.execute_script(
            "fireMultiColumnComboClick('FRMTimestampDeptPosCombo',{});".format(idx)
        )

    @cached_property
    def timetable(self):
        self.driver.find_element_by_id("anchorFolderTabs2").click()
        table = self.driver.find_elements_by_xpath(
            "//*[contains(@id, 'TimeEntriesRepeater')]"
        )

        header = self.driver.find_elements_by_xpath(
            "//*[@id='TimeEntriesHeader']/tr/th"
        )

        return self.make_dataframe_from_html(table, 'td', header)

    @cached_property
    def totals(self):
        """Return the total hours worked in the current period."""
        self.driver.find_element_by_id("anchorFolderTabs2").click()
        totals = self.driver.find_element_by_xpath(
            "//*[@id='TimeEntriesTotalTable']/tbody/tr[@id='trTotalWorked']"
        )

        return {
            "totalHours": totals.find_element_by_xpath("td[2]/p/span").text,
            "hourPayCodeTotal": totals.find_element_by_xpath("td[4]/p/span").text,
            "dollarPayCodeTotal": totals.find_element_by_xpath("td[6]/p/span").text,
            "projectTotal": totals.find_element_by_xpath("td[8]/p/span").text
        }

    @cached_property
    def periods(self):
        return Select(self.driver.find_element_by_id("FRMTimePeriod"))

    @property
    def period(self):
        """Return the currently selected pay period."""
        return self.periods.all_selected_options[0].text

    @period.setter
    def period(self, args):
        """Set the requested time period."""
        fields = ["FRMFrom", "FRMTo"]

        if isinstance(args, list):
            # We have a date range.
            self.periods.select_by_visible_text(Periods.Custom.value)
            dates = [arg.strftime("%x") for arg in args]
            self.map_input(zip(fields, dates))

            self.driver.find_element_by_id("bttRefresh").click()
        else:
            # We have a single element.
            self.periods.select_by_visible_text(args.value)

        # reset all properties that depend upon this
        del self.timetable
        del self.totals
