# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2018-2019 Fetch.AI Limited
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""This package contains the models of the yoti_user skill."""

from typing import Dict

from aea.skills.base import Model


YOTI_BUTTON_SCHEMA = """
<head>
  <script src="https://www.yoti.com/share/client/"></script>
</head>

<body>
  <!-- Yoti element will be rendered inside this DOM node -->
  <div id="yotiButton"></div>

  <!-- This script snippet will also be required in your HTML body -->
  <script>
    window.Yoti.Share.init({{
      elements: [
        {{
          domId: "yotiButton",
          scenarioId: "{scenario_id}",
          clientSdkId: "{client_sdk_id}",
          type: "inline",
          displayLearnMoreLink: true,
          qr: {{
            title: " Scan with the Yoti app to verify your identity and"
          }}
        }}
      ]
    }});
  </script>
</body>
"""

FAILURE = """
<body>
no address or token found
</body>
"""

SUCCESS = """
<body>
token found
</body>
"""

INFO = """
<body>
info: {info}
</body>
"""


class Parameters(Model):
    """This class represents a parameters model."""

    def __init__(self, **kwargs):
        """Initialize the parameters."""
        scenario_id = kwargs.pop("yoti_scenario_id")
        client_sdk_id = kwargs.pop("yoti_client_sdk_id")
        if scenario_id is None or client_sdk_id is None:
            raise ValueError("yoti_scenario_id or yoti_client_sdk_id not provided.")
        super().__init__(**kwargs)
        self._yoti_button = YOTI_BUTTON_SCHEMA.format(scenario_id=scenario_id, client_sdk_id=client_sdk_id)
        self._db = {}  # temporary db

    @property
    def db(self) -> Dict[str, Dict[str, str]]:
        """Get db."""
        return self._db

    @property
    def yoti_button(self) -> bytes:
        """Get yoti button."""
        return self._yoti_button.encode("utf-8")

    @property
    def success_html(self):
        """Get success html."""
        return SUCCESS.encode("utf-8")

    @property
    def failure_html(self):
        """Get success html."""
        return FAILURE.encode("utf-8")

    @staticmethod
    def info_html(info: Dict[str, str]):
        """Get no_address html."""
        return INFO.format(info=info).encode("utf-8")
