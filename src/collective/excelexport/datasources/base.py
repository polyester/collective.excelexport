from zope.interface import implements
from zope.component import getAdapters
from zope.component import getUtility

from plone import api
from plone.behavior.interfaces import IBehavior

from collective.excelexport.interfaces import IDataSource
from collective.excelexport.interfaces import IExportableFactory


class BaseContentsDataSource(object):
    """
    Base class for a datasource that exports contents
    Gets the fields and objects to serialize in excel file
    provided by a named adapter that adapts the fti, the context and the request

    group them by portal type (one sheet by portal type)
    """
    implements(IDataSource)
    excluded_factories = None
    excluded_exportables = None

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def get_filename(self):
        """Gets the file name (without extension) of the exported excel
        """
        raise NotImplemented

    def get_objects(self):
        raise NotImplemented

    def filter_exportables(self, exportables):
        """Filter exportables whose field name is not in excluded_exportables

        Override this method if you want to implement specific filtering
        """
        if self.excluded_exportables is None:
            return exportables
        else:
            filtered_exportables = []
            for exportable in exportables:
                try:
                    field_name = exportable.field.__name__
                    if field_name not in self.excluded_exportables:
                        filtered_exportables.append(exportable)
                except AttributeError:
                    filtered_exportables.append(exportable)

            return filtered_exportables

    def get_factories(self, p_type_fti):
        factories = getAdapters((p_type_fti, self.context, self.request),
                                IExportableFactory)
        filtered_factories = []
        for factory_name, factory in sorted(factories, key=lambda f: f[1].weight):
            if factory.portal_types and p_type_fti.id not in factory.portal_types:
                # filter on content types if it is set
                continue
            elif self.excluded_factories and factory_name in self.excluded_factories:
                # exclude factory if there is a factory filter
                continue
            elif factory.behaviors:
                # filter on behaviors if factory is restricted to a behavior
                for behavior_id in p_type_fti.behaviors:
                    behavior = getUtility(IBehavior, behavior_id).interface
                    if behavior in factory.behaviors:
                        break
                else:
                    continue

            filtered_factories.append(factory)

        return filtered_factories

    def get_sheets_data(self):
        """Gets a list of dictionaries with three keys :
            title: the title of the sheet
            objects: the list of objects
            exportables: the exportables to render
        """
        objects = self.get_objects()
        p_types_objects = {}
        for obj in objects:
            p_types_objects.setdefault(obj.portal_type, []).append(obj)

        ttool = api.portal.get_tool('portal_types')
        data = []
        for p_type in sorted(p_types_objects.keys()):
            # get exportables for each content type
            p_type_fti = ttool[p_type]
            factories = self.get_factories(p_type_fti)

            # get the list of exportables from factories
            exportables = []
            for factory in factories:
                exportables.extend(factory.get_exportables())

            title = p_type_fti.Title()
            data.append({'title': title,
                         'objects': p_types_objects[p_type],
                         'exportables': self.filter_exportables(exportables)
                        })

        return data
