import json

from bika.lims import api
from bika.lims.browser.analyses import AnalysesView
from bika.lims.browser.analysisrequest.sections import LabAnalysesSection
from bika.lims.catalog import SETUP_CATALOG
from bika.lims.utils import get_link
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from senaite.ast import is_installed
from senaite.ast import messageFactory as _


class ASTAnalysesSection(LabAnalysesSection):
    """Field analyses section adapter for Sample view
    """
    order = 20
    title = _("Antibiotic Sensitivity")
    capture = "ast"

    def is_visible(self):
        """Returns true if senaite.ast is installed
        """
        return is_installed()


class ManageResultsView(AnalysesView):
    """Listing view for AST results entry
    """
    contents_table_template = ViewPageTemplateFile("templates/ast_results.pt")

    def __init__(self, context, request):
        super(ManageResultsView, self).__init__(context, request)

        self.contentFilter.update({
            "getPointOfCapture": "ast",
        })

        self.form_id = "ast_analyses"
        self.allow_edit = True
        self.show_workflow_action_buttons = True
        self.show_search = False

        self.columns["Service"].update({
            "title": _("Microorganism"),
        })

        # Remove the columns we are not interested in from review_states
        hide = ["Method", "Instrument", "Analyst", "DetectionLimitOperand",
                "Specification", "Uncertainty", "retested", "Attachments",
                "DueDate"]

        for review_state in self.review_states:
            columns = filter(lambda c: c not in hide, review_state["columns"])
            review_state.update({"columns": columns})

    def folderitem(self, obj, item, index):
        item['Service'] = obj.Title
        item['class']['service'] = 'service_title'
        item['service_uid'] = obj.getServiceUID
        item['Keyword'] = obj.getKeyword

        # Append info link before the service
        # see: bika.lims.site.coffee for the attached event handler
        item["before"]["Service"] = get_link(
            "analysisservice_info?service_uid={}&analysis_uid={}"
                .format(obj.getServiceUID, obj.UID),
            value="<i class='fas fa-info-circle'></i>",
            css_class="service_info")

        # Note that getSampleTypeUID returns the type of the Sample, no matter
        # if the sample associated to the analysis is a regular Sample (routine
        # analysis) or if is a Reference Sample (Reference Analysis). If the
        # analysis is a duplicate, it returns the Sample Type of the sample
        # associated to the source analysis.
        item['st_uid'] = obj.getSampleTypeUID

        # Fill item's row class
        self._folder_item_css_class(obj, item)
        # Fill result and/or result options
        self._folder_item_result(obj, item)
        # Fill calculation and interim fields
        self._folder_item_calculation(obj, item)
        # Fill submitted by
        self._folder_item_submitted_by(obj, item)
        # Fill Partition
        self._folder_item_partition(obj, item)
        # Fill verification criteria
        self._folder_item_verify_icons(obj, item)
        # Fill worksheet anchor/icon
        self._folder_item_assigned_worksheet(obj, item)
        # Fill hidden field (report visibility)
        self._folder_item_report_visibility(obj, item)
        # Renders remarks toggle button
        self._folder_item_remarks(obj, item)

        return item

    def folderitems(self):
        # This shouldn't be required here, but there are some views that calls
        # directly contents_table() instead of __call__, so before_render is
        # never called. :(
        self.before_render()

        # Get all items
        # Note we call AnalysesView's base class!
        items = super(AnalysesView, self).folderitems()

        # TAL requires values for all interim fields on all items, so we set
        # blank values in unused cells
        for item in items:
            for field in self.interim_columns:
                if field not in item:
                    item[field] = ""

        # XXX order the list of interim columns
        interim_keys = self.interim_columns.keys()
        interim_keys.reverse()

        # Add InterimFields keys (Antibiotic abbreviations) to columns
        for col_id in interim_keys:
            if col_id not in self.columns:
                self.columns[col_id] = {
                    "title": self.interim_columns[col_id],
                    "input_width": "2",
                    "input_class": "ajax_calculate string",
                    "sortable": False,
                    "toggle": True,
                    "ajax": True,
                }

        if self.allow_edit:
            new_states = []
            for state in self.review_states:
                # Resort interim fields
                columns = state["columns"]
                position = columns.index("Result")
                for col_id in interim_keys:
                    if col_id not in columns:
                        columns.insert(position, col_id)

                state.update({"columns": columns})
                new_states.append(state)

            self.review_states = new_states
            self.show_select_column = True

        self.json_interim_fields = json.dumps(self.interim_fields)
        self.items = items

        return items

    def get_children_hook(self, parent_uid, child_uids=None):
        """Hook to get the children of an item
        """
        super(ManageResultsView, self).get_children_hook(
            parent_uid, child_uids=child_uids)

    def get_panels(self):
        query = {
            "portal_type": "ASTPanel",
            "sort_on": "sortable_title",
            "sort_order": "ascending",
            "is_active": True,
        }
        brains = api.search(query, SETUP_CATALOG)
        return map(self.get_panel_info, brains)

    def get_panel_info(self, uid_brain_object):
        obj = api.get_object(uid_brain_object)
        return {
            "uid": api.get_uid(obj),
            "title": api.get_title(obj),
        }