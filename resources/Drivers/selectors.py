"""
RPA Challenge page selectors, independent of any library.

In a module of their own because they describe the **site**, not the tool: both
drivers attack the same page. A copy per driver would mean fixing a DOM change
twice, and the claim that both locate elements the same way would rest on
discipline instead of being verifiable - which is what the benchmark needs.
"""

XPATH_FIELD_BY_LABEL = "//label[text()='{label}']/following-sibling::input"
"""
Input field that is a sibling of the visible label. Format with the field name.

Locating by label is mandatory, not a preference: the challenge **shuffles the
order of the fields on every round**. Any positional selector would fill in the
wrong field — which is precisely the trap the site sets.
"""

XPATH_START_BUTTON = "//button[text()='Start']"
"""<button ...>Start</button>"""

XPATH_SUBMIT_BUTTON = "//input[@type='submit' and @value='Submit']"
"""
<input type="submit" value="Submit"> — **not** a <button>.

The asymmetry between the two buttons is real and worth knowing: the earlier
code used `get_by_role('button', name='Submit')` and worked, because
Playwright's accessibility engine gives an input[type=submit] the button role
and takes its name from the `value` attribute. Selenium has no such
abstraction. Writing the selector explicitly is what lets both drivers use the
same string — and avoids crediting Selenium with a difficulty that was only a
lack of syntactic sugar.
"""

XPATH_RESULT = "//*[contains(text(),'Your success rate')]"
"""
The challenge's closing message, something like
'Your success rate is 100% (70 out of 70 fields) in 807 milliseconds'.

The fill time the benchmark uses comes from here — a measurement made by the
site itself, independent of our own stopwatch.
"""
