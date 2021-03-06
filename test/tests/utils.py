# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Nebula, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import datetime
import os

from django.core.exceptions import ValidationError  # noqa
import django.template
from django.template import defaultfilters

from horizon.test import helpers as test
from horizon.utils import fields
from horizon.utils import filters
# we have to import the filter in order to register it
from horizon.utils.filters import parse_isotime  # noqa
from horizon.utils import memoized
from horizon.utils import secret_key
from horizon.utils import validators


class ValidatorsTests(test.TestCase):
    def test_validate_ipv4_cidr(self):
        GOOD_CIDRS = ("192.168.1.1/16",
                      "192.0.0.1/17",
                      "0.0.0.0/16",
                      "10.144.11.107/4",
                      "255.255.255.255/0",
                      "0.1.2.3/16",
                      "0.0.0.0/32",
                      # short form
                      "128.0/16",
                      "128/4")
        BAD_CIDRS = ("255.255.255.256\\",
                     "256.255.255.255$",
                     "1.2.3.4.5/41",
                     "0.0.0.0/99",
                     "127.0.0.1/",
                     "127.0.0.1/33",
                     "127.0.0.1/-1",
                     "127.0.0.1/100",
                     # some valid IPv6 addresses
                     "fe80::204:61ff:254.157.241.86/4",
                     "fe80::204:61ff:254.157.241.86/0",
                     "2001:0DB8::CD30:0:0:0:0/60",
                     "2001:0DB8::CD30:0/90")
        ip = fields.IPField(mask=True, version=fields.IPv4)
        for cidr in GOOD_CIDRS:
            self.assertIsNone(ip.validate(cidr))
        for cidr in BAD_CIDRS:
            self.assertRaises(ValidationError, ip.validate, cidr)

    def test_validate_ipv6_cidr(self):
        GOOD_CIDRS = ("::ffff:0:0/56",
                      "2001:0db8::1428:57ab/17",
                      "FEC0::/10",
                      "fe80::204:61ff:254.157.241.86/4",
                      "fe80::204:61ff:254.157.241.86/0",
                      "2001:0DB8::CD30:0:0:0:0/60",
                      "2001:0DB8::CD30:0/90",
                      "::1/128")
        BAD_CIDRS = ("1111:2222:3333:4444:::/",
                     "::2222:3333:4444:5555:6666:7777:8888:\\",
                     ":1111:2222:3333:4444::6666:1.2.3.4/1000",
                     "1111:2222::4444:5555:6666::8888@",
                     "1111:2222::4444:5555:6666:8888/",
                     "::ffff:0:0/129",
                     "1.2.3.4:1111:2222::5555//22",
                     "fe80::204:61ff:254.157.241.86/200",
                     # some valid IPv4 addresses
                      "10.144.11.107/4",
                      "255.255.255.255/0",
                      "0.1.2.3/16")
        ip = fields.IPField(mask=True, version=fields.IPv6)
        for cidr in GOOD_CIDRS:
            self.assertIsNone(ip.validate(cidr))
        for cidr in BAD_CIDRS:
            self.assertRaises(ValidationError, ip.validate, cidr)

    def test_validate_mixed_cidr(self):
        GOOD_CIDRS = ("::ffff:0:0/56",
                      "2001:0db8::1428:57ab/17",
                      "FEC0::/10",
                      "fe80::204:61ff:254.157.241.86/4",
                      "fe80::204:61ff:254.157.241.86/0",
                      "2001:0DB8::CD30:0:0:0:0/60",
                      "0.0.0.0/16",
                      "10.144.11.107/4",
                      "255.255.255.255/0",
                      "0.1.2.3/16",
                      # short form
                      "128.0/16",
                      "10/4")
        BAD_CIDRS = ("1111:2222:3333:4444::://",
                     "::2222:3333:4444:5555:6666:7777:8888:",
                     ":1111:2222:3333:4444::6666:1.2.3.4/1/1",
                     "1111:2222::4444:5555:6666::8888\\2",
                     "1111:2222::4444:5555:6666:8888/",
                     "1111:2222::4444:5555:6666::8888/130",
                     "127.0.0.1/",
                     "127.0.0.1/33",
                     "127.0.0.1/-1")
        ip = fields.IPField(mask=True, version=fields.IPv4 | fields.IPv6)
        for cidr in GOOD_CIDRS:
            self.assertIsNone(ip.validate(cidr))
        for cidr in BAD_CIDRS:
            self.assertRaises(ValidationError, ip.validate, cidr)

    def test_validate_IPs(self):
        GOOD_IPS_V4 = ("0.0.0.0",
                      "10.144.11.107",
                      "169.144.11.107",
                      "172.100.11.107",
                      "255.255.255.255",
                      "0.1.2.3")
        GOOD_IPS_V6 = ("",
                      "::ffff:0:0",
                      "2001:0db8::1428:57ab",
                      "FEC0::",
                      "fe80::204:61ff:254.157.241.86",
                      "fe80::204:61ff:254.157.241.86",
                      "2001:0DB8::CD30:0:0:0:0")
        BAD_IPS_V4 = ("1111:2222:3333:4444:::",
                     "::2222:3333:4444:5555:6666:7777:8888:",
                     ":1111:2222:3333:4444::6666:1.2.3.4",
                     "1111:2222::4444:5555:6666::8888",
                     "1111:2222::4444:5555:6666:8888/",
                     "1111:2222::4444:5555:6666::8888/130",
                     "127.0.0.1/",
                     "127.0.0.1/33",
                     "127.0.0.1/-1")
        BAD_IPS_V6 = ("1111:2222:3333:4444:::",
                     "::2222:3333:4444:5555:6666:7777:8888:",
                     ":1111:2222:3333:4444::6666:1.2.3.4",
                     "1111:2222::4444:5555:6666::8888",
                     "1111:2222::4444:5555:6666:8888/",
                     "1111:2222::4444:5555:6666::8888/130")
        ipv4 = fields.IPField(required=True, version=fields.IPv4)
        ipv6 = fields.IPField(required=False, version=fields.IPv6)
        ipmixed = fields.IPField(required=False,
                                 version=fields.IPv4 | fields.IPv6)

        for ip_addr in GOOD_IPS_V4:
            self.assertIsNone(ipv4.validate(ip_addr))
            self.assertIsNone(ipmixed.validate(ip_addr))

        for ip_addr in GOOD_IPS_V6:
            self.assertIsNone(ipv6.validate(ip_addr))
            self.assertIsNone(ipmixed.validate(ip_addr))

        for ip_addr in BAD_IPS_V4:
            self.assertRaises(ValidationError, ipv4.validate, ip_addr)
            self.assertRaises(ValidationError, ipmixed.validate, ip_addr)

        for ip_addr in BAD_IPS_V6:
            self.assertRaises(ValidationError, ipv6.validate, ip_addr)
            self.assertRaises(ValidationError, ipmixed.validate, ip_addr)

        self.assertRaises(ValidationError, ipv4.validate, "")  # required=True

        iprange = fields.IPField(required=False,
                                 mask=True,
                                 mask_range_from=10,
                                 version=fields.IPv4 | fields.IPv6)
        self.assertRaises(ValidationError, iprange.validate,
                          "fe80::204:61ff:254.157.241.86/6")
        self.assertRaises(ValidationError, iprange.validate,
                          "169.144.11.107/8")
        self.assertIsNone(iprange.validate("fe80::204:61ff:254.157.241.86/36"))
        self.assertIsNone(iprange.validate("169.144.11.107/18"))

    def test_validate_multi_ip_field(self):
        GOOD_CIDRS_INPUT = ("192.168.1.1/16, 192.0.0.1/17",)
        BAD_CIDRS_INPUT = ("1.2.3.4.5/41,0.0.0.0/99",
                           "1.2.3.4.5/41;0.0.0.0/99",
                           "1.2.3.4.5/41   0.0.0.0/99",
                           "192.168.1.1/16 192.0.0.1/17")

        ip = fields.MultiIPField(mask=True, version=fields.IPv4)
        for cidr in GOOD_CIDRS_INPUT:
            self.assertIsNone(ip.validate(cidr))
        for cidr in BAD_CIDRS_INPUT:
            self.assertRaises(ValidationError, ip.validate, cidr)

    def test_port_validator(self):
        VALID_PORTS = (-1, 65535)
        INVALID_PORTS = (-2, 65536)

        for port in VALID_PORTS:
            self.assertIsNone(validators.validate_port_range(port))

        for port in INVALID_PORTS:
            self.assertRaises(ValidationError,
                              validators.validate_port_range,
                              port)

    def test_ip_proto_validator(self):
        VALID_PROTO = (-1, 255)
        INVALID_PROTO = (-2, 256)

        for proto in VALID_PROTO:
            self.assertIsNone(validators.validate_ip_protocol(proto))

        for proto in INVALID_PROTO:
            self.assertRaises(ValidationError,
                              validators.validate_ip_protocol,
                              proto)

    def test_port_range_validator(self):
        VALID_RANGE = ('1:65535',
                       '-1:-1')
        INVALID_RANGE = ('22:22:22:22',
                         '-1:65536')

        test_call = validators.validate_port_or_colon_separated_port_range
        for prange in VALID_RANGE:
            self.assertIsNone(test_call(prange))

        for prange in INVALID_RANGE:
            self.assertRaises(ValidationError, test_call, prange)


class SecretKeyTests(test.TestCase):
    def test_generate_secret_key(self):
        key = secret_key.generate_key(32)
        self.assertEqual(len(key), 32)
        self.assertNotEqual(key, secret_key.generate_key(32))

    def test_generate_or_read_key_from_file(self):
        key_file = ".test_secret_key_store"
        key = secret_key.generate_or_read_from_file(key_file)

        # Consecutive reads should come from the already existing file:
        self.assertEqual(key, secret_key.generate_or_read_from_file(key_file))

        # Key file only be read/writable by user:
        self.assertEqual(oct(os.stat(key_file).st_mode & 0o777), "0600")
        os.chmod(key_file, 0o777)
        self.assertRaises(secret_key.FilePermissionError,
                          secret_key.generate_or_read_from_file, key_file)
        os.remove(key_file)


class FiltersTests(test.TestCase):
    def test_replace_underscore_filter(self):
        res = filters.replace_underscores("__under_score__")
        self.assertEqual(res, "  under score  ")

    def test_parse_isotime_filter(self):
        c = django.template.Context({'time': ''})
        t = django.template.Template('{{time|parse_isotime}}')
        output = u""

        self.assertEqual(t.render(c), output)

        c = django.template.Context({'time': 'error'})
        t = django.template.Template('{{time|parse_isotime}}')
        output = u""

        self.assertEqual(t.render(c), output)

        c = django.template.Context({'time': 'error'})
        t = django.template.Template('{{time|parse_isotime:"test"}}')
        output = u"test"

        self.assertEqual(t.render(c), output)

        c = django.template.Context({'time': '2007-03-04T21:08:12'})
        t = django.template.Template('{{time|parse_isotime:"test"}}')
        output = u"March 4, 2007, 3:08 p.m."

        self.assertEqual(t.render(c), output)

        adate = '2007-01-25T12:00:00Z'
        result = filters.parse_isotime(adate)
        self.assertIsInstance(result, datetime.datetime)


class TimeSinceNeverFilterTests(test.TestCase):

    default = u"Never"

    def test_timesince_or_never_returns_default_for_empty_string(self):
        c = django.template.Context({'time': ''})
        t = django.template.Template('{{time|timesince_or_never}}')
        self.assertEqual(t.render(c), self.default)

    def test_timesince_or_never_returns_default_for_none(self):
        c = django.template.Context({'time': None})
        t = django.template.Template('{{time|timesince_or_never}}')
        self.assertEqual(t.render(c), self.default)

    def test_timesince_or_never_returns_default_for_gibberish(self):
        c = django.template.Context({'time': django.template.Context()})
        t = django.template.Template('{{time|timesince_or_never}}')
        self.assertEqual(t.render(c), self.default)

    def test_timesince_or_never_returns_with_custom_default(self):
        custom = "Hello world"
        c = django.template.Context({'date': ''})
        t = django.template.Template('{{date|timesince_or_never:"%s"}}'
                                     % custom)
        self.assertEqual(t.render(c), custom)

    def test_timesince_or_never_returns_with_custom_empty_string_default(self):
        c = django.template.Context({'date': ''})
        t = django.template.Template('{{date|timesince_or_never:""}}')
        self.assertEqual(t.render(c), "")

    def test_timesince_or_never_returns_same_output_as_django_date(self):
        d = datetime.date(year=2014, month=3, day=7)
        c = django.template.Context({'date': d})
        t = django.template.Template('{{date|timesince_or_never}}')
        self.assertEqual(t.render(c), defaultfilters.timesince(d))

    def test_timesince_or_never_returns_same_output_as_django_datetime(self):
        now = datetime.datetime.now()
        c = django.template.Context({'date': now})
        t = django.template.Template('{{date|timesince_or_never}}')
        self.assertEqual(t.render(c), defaultfilters.timesince(now))


class MemoizedTests(test.TestCase):
    def test_memoized_decorator_cache_on_next_call(self):
        values_list = []

        @memoized.memoized
        def cache_calls(remove_from):
            values_list.append(remove_from)
            return True

        def non_cached_calls(remove_from):
            values_list.append(remove_from)
            return True

        for x in range(0, 5):
            non_cached_calls(1)
        self.assertEqual(len(values_list), 5)

        values_list = []
        for x in range(0, 5):
            cache_calls(1)
        self.assertEqual(len(values_list), 1)
