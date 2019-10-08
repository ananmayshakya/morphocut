import csv
import os

from morphocut._optional import import_optional_dependency
from morphocut import Node, Output


def _default_writer(dataframe, path_or_buf):
    dataframe.to_csv(path_or_buf, index=False)


class PandasWriter(Node):
    """Create a duplicate file and dumps metadata here."""

    def __init__(
        self,
        path_or_buf,
        data,
        columns=None,
        drop_duplicates_subset=None,
        writer=_default_writer,
    ):
        super().__init__()

        self.path_or_buf = path_or_buf
        self.data = data
        self.columns = columns
        self.drop_duplicates_subset = drop_duplicates_subset
        self.dataframe = []
        self.writer = writer

        self._pd = import_optional_dependency("pandas")

    def transform(self, data):
        if self.columns:
            data = {k: data.get(k, None) for k in self.columns}

        self.dataframe.append(data)

    def after_stream(self):
        dataframe = self._pd.DataFrame(self.dataframe)

        if self.drop_duplicates_subset is not None:
            dataframe.drop_duplicates(
                subset=self.drop_duplicates_subset,
                inplace=True,
            )

        self.writer(dataframe, self.path_or_buf)


@Output("meta_out")
class JoinMetadata(Node):
    """Join information from a CSV/TSV/Excel/... file."""

    def __init__(self, filename, data=None, on=None, fields=None):
        super().__init__()

        self.data = data
        self.on = on

        pd = import_optional_dependency("pandas")

        ext = os.path.splitext(filename)[1]

        if ext in (".xls", ".xlsx"):
            dataframe = pd.read_excel(filename, usecols=fields)
        else:
            with open('example.csv', newline='') as csvfile:
                dialect = csv.Sniffer().sniff(csvfile.read(1024))
            dataframe = pd.read_csv(filename, dialect=dialect, usecols=fields)

        dataframe.set_index(self.on, inplace=True, verify_integrity=True)

        self.dataframe = dataframe

    def transform(self, data):
        if data is None:
            data = {}

        key = data[self.on]

        row = self.dataframe.loc[key].to_dict()

        return {**data, **row}
