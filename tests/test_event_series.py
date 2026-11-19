import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from events import (
    Event, SubEvent, NewEventInfo, NewSubEventInfo, NewEventSeriesInfo,
    make_subevent_name, next_weekday, prompt_subevents
)
from client import Client
from lang import Lang
from operations import (
    setup_subevent_quotas,
    cleanup_base_quotas,
    update_subevent_latecomer_dates,
    create_new_event_series,
    add_subevents_to_series,
    clean_quota_name,
    get_quota_templates_for_series,
    choose_event,
)


class TestEventModels(unittest.TestCase):
    def test_event_has_subevents_flag(self):
        ev = Event(
            name={"en": "Series", "de-informal": "Serie"},
            slug="test-series",
            live=False,
            date_from="2026-11-20T10:00:00",
            date_to="2026-12-20T12:00:00",
            public_url="https://pretix.eu/org/test-series/",
            location={"en": "Berlin"},
            has_subevents=True,
            default_lang=Lang.DE
        )
        self.assertTrue(ev.has_subevents)
        self.assertEqual(ev.slug, "test-series")
        self.assertEqual(ev.get_name(), "Serie")
        self.assertIn("has_subevents=True", repr(ev))

    def test_event_with_none_dates(self):
        ev = Event(
            name={"en": "No dates"},
            slug="no-dates",
            live=False,
            date_from=None,
            date_to=None,
            public_url="",
            location={},
            has_subevents=True
        )
        self.assertIsNone(ev.date_from)
        self.assertIsNone(ev.date_to)
        self.assertIn("None", repr(ev))

    def test_subevent_model(self):
        data = {
            "id": 42,
            "name": {"en": "Session 1", "de-informal": "Termin 1"},
            "event": "test-series",
            "active": False,
            "is_public": True,
            "date_from": "2026-11-21T11:00:00",
            "date_to": "2026-11-21T13:00:00",
            "date_admission": None,
            "presale_start": None,
            "presale_end": None,
            "location": {"en": "Room 101"},
            "frontpage_text": {"en": "Description"},
            "comment": "Internal note",
            "item_price_overrides": [{"item": 1, "price": "10.00"}],
            "variation_price_overrides": [],
            "meta_data": {}
        }
        sub = SubEvent.from_dict(data, default_lang=Lang.EN)
        self.assertEqual(sub.id, 42)
        self.assertEqual(sub.event, "test-series")
        self.assertEqual(sub.get_name(), "Session 1")
        self.assertEqual(sub.date_from, datetime(2026, 11, 21, 11, 0, 0))
        self.assertEqual(sub.date_to, datetime(2026, 11, 21, 13, 0, 0))
        self.assertEqual(sub.location, {"en": "Room 101"})
        self.assertEqual(sub.comment, "Internal note")
        self.assertEqual(len(sub.item_price_overrides), 1)

    def test_new_subevent_info_to_data(self):
        dt_from = datetime(2026, 12, 1, 10, 0, 0)
        dt_to = datetime(2026, 12, 1, 12, 0, 0)
        info = NewSubEventInfo(
            name={"en": "Session 1"},
            date_from=dt_from,
            date_to=dt_to,
            active=False,
            is_public=True,
            location={"en": "Lab 1"},
            comment="Test comment",
            item_price_overrides=[{"item": 5, "price": None}]
        )
        d = info.to_data()
        self.assertEqual(d["name"], {"en": "Session 1"})
        self.assertEqual(d["date_from"], dt_from.isoformat())
        self.assertEqual(d["date_to"], dt_to.isoformat())
        self.assertFalse(d["active"])
        self.assertTrue(d["is_public"])
        self.assertEqual(d["location"], {"en": "Lab 1"})
        self.assertEqual(d["comment"], "Test comment")
        self.assertEqual(d["item_price_overrides"], [{"item": 5, "price": None}])

    def test_new_event_series_info_to_data(self):
        dt_from = datetime(2026, 12, 1, 10, 0, 0)
        dt_to = datetime(2026, 12, 22, 12, 0, 0)
        info = NewEventSeriesInfo(
            slug="series-slug",
            name={"en": "Series Name"},
            date_from=dt_from,
            date_to=dt_to,
            subevents=[NewSubEventInfo(name={"en": "S1"}, date_from=dt_from, date_to=dt_to)]
        )
        self.assertTrue(info.has_subevents)
        d = info.to_data()
        self.assertTrue(d["has_subevents"])
        self.assertEqual(d["slug"], "series-slug")
        self.assertEqual(len(info.subevents), 1)

    def test_make_subevent_name(self):
        base = {"de-informal": "Roboter", "en": "Robots"}
        res = make_subevent_name(base, 2)
        self.assertEqual(res["de-informal"], "Roboter - Termin 2")
        self.assertEqual(res["en"], "Robots - Session 2")

        res_custom = make_subevent_name(base, 2, "Custom Date")
        self.assertEqual(res_custom["de-informal"], "Custom Date")
        self.assertEqual(res_custom["en"], "Custom Date")


class TestClientSubevents(unittest.TestCase):
    def setUp(self):
        self.client = Client(token="dummy-token", organizer="testorg", read_only=False)

    @patch("requests.get")
    def test_get_subevents(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "count": 1,
            "next": None,
            "results": [
                {
                    "id": 10,
                    "name": {"en": "Date 1"},
                    "event": "myseries",
                    "active": False,
                    "is_public": True,
                    "date_from": "2026-11-28T11:00:00",
                    "date_to": "2026-11-28T13:00:00"
                }
            ]
        }
        mock_get.return_value = mock_resp

        subs = self.client.get_subevents("myseries")
        self.assertEqual(len(subs), 1)
        self.assertEqual(subs[0].id, 10)
        self.assertEqual(subs[0].event, "myseries")
        mock_get.assert_called_once()
        self.assertIn("/api/v1/organizers/testorg/events/myseries/subevents/", mock_get.call_args[0][0])

    @patch("requests.post")
    def test_create_subevent(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {
            "id": 11,
            "name": {"en": "Date 2"},
            "event": "myseries",
            "active": False,
            "is_public": True,
            "date_from": "2026-12-05T11:00:00",
            "date_to": "2026-12-05T13:00:00"
        }
        mock_post.return_value = mock_resp

        sub_info = NewSubEventInfo(
            name={"en": "Date 2"},
            date_from=datetime(2026, 12, 5, 11, 0, 0),
            date_to=datetime(2026, 12, 5, 13, 0, 0)
        )
        created = self.client.create_subevent("myseries", sub_info)
        self.assertEqual(created.id, 11)
        self.assertEqual(created.name["en"], "Date 2")
        mock_post.assert_called_once()

    @patch("requests.patch")
    def test_patch_subevent(self, mock_patch):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": 11, "name": {"en": "Updated"}}
        mock_patch.return_value = mock_resp

        status, data = self.client.patch_subevent("myseries", 11, {"name": {"en": "Updated"}})
        self.assertEqual(status, 200)
        mock_patch.assert_called_once()
        self.assertIn("/api/v1/organizers/testorg/events/myseries/subevents/11/", mock_patch.call_args[0][0])

    @patch("requests.patch")
    def test_patch_event(self, mock_patch):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"slug": "myseries", "date_to": "2026-12-31T12:00:00"}
        mock_patch.return_value = mock_resp

        status, data = self.client.patch_event("myseries", {"date_to": "2026-12-31T12:00:00"})
        self.assertEqual(status, 200)
        mock_patch.assert_called_once()
        self.assertIn("/api/v1/organizers/testorg/events/myseries/", mock_patch.call_args[0][0])

    @patch("requests.delete")
    def test_delete_subevent(self, mock_delete):
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        mock_delete.return_value = mock_resp

        self.client.delete_subevent("myseries", 11)
        mock_delete.assert_called_once()
        self.assertIn("/api/v1/organizers/testorg/events/myseries/subevents/11/", mock_delete.call_args[0][0])

    @patch("requests.get")
    def test_get_quotas(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "count": 1,
            "next": None,
            "results": [{"id": 100, "name": "Tickets", "size": 15, "subevent": 10}]
        }
        mock_get.return_value = mock_resp

        quotas = self.client.get_quotas("myseries", subevent_id=10)
        self.assertEqual(len(quotas), 1)
        self.assertEqual(quotas[0]["id"], 100)
        self.assertIn("subevent=10", mock_get.call_args[0][0])

    @patch("requests.post")
    def test_create_quota(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"id": 101, "name": "Tickets 2", "size": 15}
        mock_post.return_value = mock_resp

        status, data = self.client.create_quota("myseries", {"name": "Tickets 2", "size": 15})
        self.assertEqual(status, 201)
        self.assertEqual(data["id"], 101)

    @patch("requests.delete")
    def test_delete_quota(self, mock_delete):
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        mock_delete.return_value = mock_resp

        self.client.delete_quota("myseries", 101)
        mock_delete.assert_called_once()
        self.assertIn("/api/v1/organizers/testorg/events/myseries/quotas/101/", mock_delete.call_args[0][0])


class TestOperations(unittest.TestCase):
    def test_setup_subevent_quotas(self):
        client = MagicMock()
        event = Event(
            name={"en": "Series"}, slug="series", live=False,
            date_from="2026-11-20T10:00:00", date_to="2026-12-20T12:00:00",
            public_url="", location={}, has_subevents=True
        )
        subevent = SubEvent(
            id=5, name={"en": "Sub 1"}, event="series", active=False, is_public=True,
            date_from="2026-11-28T11:00:00", date_to="2026-11-28T13:00:00"
        )
        base_quotas = [
            {"id": 1, "name": "Standard", "size": 12, "items": [1, 2], "variations": [], "subevent": None}
        ]

        setup_subevent_quotas(client, event, subevent, base_quotas)
        client.create_quota.assert_called_once()
        created_quota = client.create_quota.call_args[0][1]
        self.assertEqual(created_quota["subevent"], 5)
        self.assertEqual(created_quota["size"], 12)
        self.assertEqual(created_quota["items"], [1, 2])
        self.assertIn("Standard (28.11.2026)", created_quota["name"])

    def test_cleanup_base_quotas(self):
        client = MagicMock()
        event = Event(
            name={"en": "Series"}, slug="series", live=False,
            date_from="2026-11-20T10:00:00", date_to="2026-12-20T12:00:00",
            public_url="", location={}, has_subevents=True
        )
        base_quotas = [
            {"id": 1, "name": "Standard", "size": 12, "items": [1], "subevent": None},
            {"id": 2, "name": "Other", "size": 5, "items": [2], "subevent": None}
        ]
        cleanup_base_quotas(client, event, base_quotas)
        self.assertEqual(client.delete_quota.call_count, 2)
        client.delete_quota.assert_any_call(event, 1)
        client.delete_quota.assert_any_call(event, 2)

    def test_update_subevent_latecomer_dates(self):
        client = MagicMock()
        event = Event(
            name={"en": "Series"}, slug="series", live=False,
            date_from="2026-11-20T10:00:00", date_to="2026-12-20T12:00:00",
            public_url="", location={}, has_subevents=True
        )
        subevent = SubEvent(
            id=7, name={"en": "Sub 1"}, event="series", active=False, is_public=True,
            date_from=datetime(2026, 12, 10, 11, 0, 0), date_to=datetime(2026, 12, 10, 13, 0, 0)
        )
        mock_product = MagicMock()
        mock_product.id = 99
        mock_product.get_name.return_value = "Latecomer Ticket"

        update_subevent_latecomer_dates(client, event, subevent, latecomer_ticket=mock_product)
        client.patch_subevent.assert_called_once()
        patch_data = client.patch_subevent.call_args[0][2]
        self.assertIn("item_price_overrides", patch_data)
        override = patch_data["item_price_overrides"][0]
        self.assertEqual(override["item"], 99)
        self.assertEqual(override["available_from"], "2026-12-07T01:00:00")

    @patch("operations.choose_event")
    @patch("operations.NewEventSeriesInfo.from_user_input")
    @patch("operations.change_description")
    def test_create_new_event_series_flow(self, mock_change_desc, mock_from_input, mock_choose):
        client = MagicMock()
        template = Event(
            name={"en": "Template"}, slug="template", live=False,
            date_from="2026-11-20T10:00:00", date_to="2026-12-20T12:00:00",
            public_url="", location={"en": "Berlin"}
        )
        mock_choose.return_value = template

        dt1_from = datetime(2026, 12, 5, 11, 0)
        dt1_to = datetime(2026, 12, 5, 13, 0)
        dt2_from = datetime(2026, 12, 12, 11, 0)
        dt2_to = datetime(2026, 12, 12, 13, 0)

        sub_info1 = NewSubEventInfo(name={"en": "Session 1"}, date_from=dt1_from, date_to=dt1_to)
        sub_info2 = NewSubEventInfo(name={"en": "Session 2"}, date_from=dt2_from, date_to=dt2_to)
        info = NewEventSeriesInfo(
            slug="new-series", name={"en": "New Series"},
            date_from=dt1_from, date_to=dt2_to,
            subevents=[sub_info1, sub_info2]
        )
        mock_from_input.return_value = info

        cloned_event = Event(
            name={"en": "Cloned Series"}, slug="new-series", live=False,
            date_from=dt1_from, date_to=dt2_to,
            public_url="", location={"en": "Berlin"}, has_subevents=True
        )
        client.clone_event.return_value = cloned_event

        client.get_quotas.return_value = [
            {"id": 1, "name": "General", "size": 15, "items": [10], "variations": [], "subevent": None}
        ]
        mock_prod = MagicMock()
        mock_prod.id = 10
        mock_prod.get_name.return_value = "Latecomer Ticket"
        client.get_event_products.return_value = [mock_prod]

        created_sub1 = SubEvent(id=101, name={"en": "S1"}, event="new-series", active=False, is_public=True, date_from=dt1_from, date_to=dt1_to)
        created_sub2 = SubEvent(id=102, name={"en": "S2"}, event="new-series", active=False, is_public=True, date_from=dt2_from, date_to=dt2_to)
        client.create_subevent.side_effect = [created_sub1, created_sub2]

        create_new_event_series(client)

        client.clone_event.assert_called_once_with(info, template)
        mock_change_desc.assert_called_once_with(client, cloned_event)
        self.assertEqual(client.create_subevent.call_count, 2)
        # Verify subevent quotas were created for both subevents
        self.assertEqual(client.create_quota.call_count, 2)
        # Verify base quota was cleaned up
        client.delete_quota.assert_called_once_with(cloned_event, 1)

    def test_clean_quota_name(self):
        self.assertEqual(clean_quota_name("Standard (28.11.2026)"), "Standard")
        self.assertEqual(clean_quota_name("Standard (42)"), "Standard")
        self.assertEqual(clean_quota_name("Standard"), "Standard")
        self.assertEqual(clean_quota_name("Workshop (Morning)"), "Workshop (Morning)")

    def test_get_quota_templates_for_series_from_base(self):
        client = MagicMock()
        event = Event(
            name={"en": "Series"}, slug="series", live=False,
            date_from="2026-11-20T10:00:00", date_to="2026-12-20T12:00:00",
            public_url="", location={}, has_subevents=True
        )
        client.get_quotas.return_value = [
            {"id": 1, "name": "General (Base)", "size": 15, "items": [1], "variations": [], "subevent": None, "close_when_sold_out": True}
        ]
        templates = get_quota_templates_for_series(client, event)
        self.assertEqual(len(templates), 1)
        self.assertEqual(templates[0]["name"], "General (Base)")
        self.assertEqual(templates[0]["size"], 15)
        self.assertTrue(templates[0]["close_when_sold_out"])

    def test_get_quota_templates_for_series_from_existing_subevent(self):
        client = MagicMock()
        event = Event(
            name={"en": "Series"}, slug="series", live=False,
            date_from="2026-11-20T10:00:00", date_to="2026-12-20T12:00:00",
            public_url="", location={}, has_subevents=True
        )
        client.get_quotas.return_value = [
            {"id": 10, "name": "Standard (28.11.2026)", "size": 10, "items": [1, 2], "variations": [], "subevent": 5},
            {"id": 11, "name": "VIP (28.11.2026)", "size": 2, "items": [3], "variations": [], "subevent": 5},
            {"id": 20, "name": "Standard (05.12.2026)", "size": 10, "items": [1, 2], "variations": [], "subevent": 6},
        ]
        templates = get_quota_templates_for_series(client, event)
        self.assertEqual(len(templates), 2)
        self.assertEqual(templates[0]["name"], "Standard")
        self.assertEqual(templates[0]["size"], 10)
        self.assertEqual(templates[1]["name"], "VIP")
        self.assertEqual(templates[1]["size"], 2)

    def test_get_quota_templates_for_series_empty(self):
        client = MagicMock()
        event = Event(
            name={"en": "Series"}, slug="series", live=False,
            date_from="2026-11-20T10:00:00", date_to="2026-12-20T12:00:00",
            public_url="", location={}, has_subevents=True
        )
        client.get_quotas.return_value = []
        templates = get_quota_templates_for_series(client, event)
        self.assertEqual(templates, [])

    def test_add_subevents_to_series_flow(self):
        client = MagicMock()
        series_event = Event(
            name={"en": "Robotics Club", "de-informal": "Roboter Club"},
            slug="robotics-series",
            live=True,
            date_from="2026-11-28T10:00:00",
            date_to="2026-12-05T12:00:00",
            public_url="",
            location={"en": "Lab 1"},
            has_subevents=True
        )

        existing_sub1 = SubEvent(
            id=1, name={"en": "Robotics Club - Session 1"}, event="robotics-series",
            active=True, is_public=True,
            date_from=datetime(2026, 11, 28, 10, 0), date_to=datetime(2026, 11, 28, 12, 0)
        )
        existing_sub2 = SubEvent(
            id=2, name={"en": "Robotics Club - Session 2"}, event="robotics-series",
            active=True, is_public=True,
            date_from=datetime(2026, 12, 5, 10, 0), date_to=datetime(2026, 12, 5, 12, 0)
        )
        client.get_subevents.return_value = [existing_sub1, existing_sub2]

        # Quotas on the series (subevent quotas from existing subevents)
        client.get_quotas.return_value = [
            {"id": 10, "name": "Tickets (28.11.2026)", "size": 15, "items": [7], "variations": [], "subevent": 1}
        ]

        # Products with latecomer ticket
        latecomer = MagicMock()
        latecomer.id = 88
        latecomer.get_name.return_value = "Latecomer Ticket"
        client.get_event_products.return_value = [latecomer]

        # New subevents to add (index should start from 3!)
        new_dt_from = datetime(2026, 12, 12, 10, 0)
        new_dt_to = datetime(2026, 12, 12, 12, 0)
        new_sub_info = NewSubEventInfo(name={}, date_from=new_dt_from, date_to=new_dt_to, has_custom_name=False)

        created_sub = SubEvent(
            id=3, name={"en": "Robotics Club - Session 3", "de-informal": "Roboter Club - Termin 3"},
            event="robotics-series", active=False, is_public=True,
            date_from=new_dt_from, date_to=new_dt_to
        )
        client.create_subevent.return_value = created_sub

        result = add_subevents_to_series(client, event=series_event, subevents=[new_sub_info])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, 3)

        # Name should have been generated with index = 3
        self.assertEqual(new_sub_info.name["en"], "Robotics Club - Session 3")
        self.assertEqual(new_sub_info.name["de-informal"], "Roboter Club - Termin 3")

        # Quotas created for new subevent with cleaned quota name
        client.create_quota.assert_called_once()
        quota_arg = client.create_quota.call_args[0][1]
        self.assertEqual(quota_arg["name"], "Tickets (12.12.2026)")
        self.assertEqual(quota_arg["subevent"], 3)
        self.assertEqual(quota_arg["size"], 15)

        # Latecomer date set
        client.patch_subevent.assert_called_once()

        # Series date_to should have been extended to 2026-12-12T12:00:00
        client.patch_event.assert_called_once_with(series_event, {"date_to": "2026-12-12T12:00:00"})

    def test_add_subevents_to_series_not_series_error(self):
        client = MagicMock()
        single_event = Event(
            name={"en": "Single Event"}, slug="single", live=True,
            date_from="2026-11-20T10:00:00", date_to="2026-11-20T12:00:00",
            public_url="", location={}, has_subevents=False
        )
        result = add_subevents_to_series(client, event=single_event, subevents=[])
        self.assertEqual(result, [])
        client.create_subevent.assert_not_called()

    @patch("operations.prompt_subevents")
    @patch("operations.choose_event")
    def test_add_subevents_to_series_interactive(self, mock_choose, mock_prompt):
        client = MagicMock()
        series_event = Event(
            name={"en": "Series"}, slug="series-slug", live=True,
            date_from="2026-11-20T10:00:00", date_to="2026-11-20T12:00:00",
            public_url="", location={}, has_subevents=True
        )
        mock_choose.return_value = series_event
        client.get_subevents.return_value = []
        client.get_quotas.return_value = []
        client.get_event_products.return_value = []

        dt_from = datetime(2026, 12, 1, 10, 0)
        dt_to = datetime(2026, 12, 1, 12, 0)
        sub_info = NewSubEventInfo(name={"en": "S1"}, date_from=dt_from, date_to=dt_to, has_custom_name=True)
        mock_prompt.return_value = [sub_info]

        created_sub = SubEvent(id=99, name={"en": "S1"}, event="series-slug", active=False, is_public=True, date_from=dt_from, date_to=dt_to)
        client.create_subevent.return_value = created_sub

        result = add_subevents_to_series(client)

        mock_choose.assert_called_once_with(client, title='Choose event series to add sub-events to', has_subevents=True)
        mock_prompt.assert_called_once_with(series_event.name, start_index=1, title="How do you want to add dates to 'series-slug'?")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, 99)

    @patch("operations.TerminalMenu")
    def test_choose_event_has_subevents_filter(self, mock_menu_cls):
        client = MagicMock()
        ev_single = Event(name={"en": "Single"}, slug="single", live=False, date_from=None, date_to=None, public_url="", has_subevents=False)
        ev_series = Event(name={"en": "Series"}, slug="series", live=False, date_from=None, date_to=None, public_url="", has_subevents=True)

        # Mock get_events with filtering
        def mock_get_events(has_subevents=None):
            events = [ev_single, ev_series]
            if has_subevents is not None:
                events = [e for e in events if e.has_subevents == has_subevents]
            return events

        client.get_events.side_effect = mock_get_events

        mock_menu = MagicMock()
        mock_menu.show.return_value = 0
        mock_menu_cls.return_value = mock_menu

        chosen = choose_event(client, title="Select series", has_subevents=True)
        self.assertEqual(chosen.slug, "series")
        client.get_events.assert_called_once_with(has_subevents=True)


if __name__ == "__main__":
    unittest.main()
