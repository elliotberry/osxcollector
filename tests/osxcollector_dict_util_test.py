"""DictUtils tests."""

from osxcollector import osxcollector


class TestDateUtils:
    def test_link_path_to_chain(self):
        empty_path = ""
        empty_chain = osxcollector.DictUtils._link_path_to_chain(empty_path)
        assert empty_chain == []

        path_as_list = ["Session", "Items"]
        chain_as_list = osxcollector.DictUtils._link_path_to_chain(path_as_list)
        assert path_as_list == chain_as_list

        path_as_tuple = ("Session", "Items")
        chain_as_tuple = osxcollector.DictUtils._link_path_to_chain(path_as_tuple)
        assert path_as_tuple == chain_as_tuple

        path_as_set = {"Session", "Items"}
        chain_as_set = osxcollector.DictUtils._link_path_to_chain(path_as_set)
        assert path_as_set == chain_as_set

        path_as_string = "Session.Items"
        chain = osxcollector.DictUtils._link_path_to_chain(path_as_string)
        assert path_as_list == chain

    def test_get_deep_by_chain(self):
        d = {
            "Session": {
                "Items": "test-items",
                "Account": ["account1", "account2"],
            },
            23: "twenty-three",
        }

        val1 = osxcollector.DictUtils._get_deep_by_chain(d, ["Session", "Items"])
        assert "test-items" == val1

        val2 = osxcollector.DictUtils._get_deep_by_chain(d, ["23"])
        assert "twenty-three" == val2

        val_default = osxcollector.DictUtils._get_deep_by_chain(d, ["User", "Name"], "John Doe")
        assert "John Doe" == val_default

    def test_get_deep(self):
        d = {
            "SessionItems": {
                "CustomListItems": "list items",
                "Default": "default list item",
            },
            "SessionId": 140,
        }

        no_path_no_default = osxcollector.DictUtils.get_deep(d)
        assert no_path_no_default is None

        no_path_default_value = osxcollector.DictUtils.get_deep(d, default=43)
        assert 43 == no_path_default_value

        wrong_path_default_value = osxcollector.DictUtils.get_deep(d, "SessionItems.ListItems", "no items")
        assert "no items" == wrong_path_default_value

        wrong_path_default_value = osxcollector.DictUtils.get_deep(d, "SessionItems.ListItems")
        assert wrong_path_default_value is None

        value = osxcollector.DictUtils.get_deep(d, "SessionItems.CustomListItems", "no items")
        assert "list items" == value
