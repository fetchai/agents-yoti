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

from typing import Dict, Tuple

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
            title: "Scan with the Yoti app to verify your {scenario_name}"
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

VALID_SCENARIO_NAMES = ["age", "identity"]


class Parameters(Model):
    """This class represents a parameters model."""

    def __init__(self, **kwargs):
        """Initialize the parameters."""
        scenario_id = kwargs.pop("yoti_scenario_id")
        if scenario_id is None:
            raise ValueError("yoti_scenario_id not provided.")
        client_sdk_id = kwargs.pop("yoti_client_sdk_id")
        if client_sdk_id is None:
            raise ValueError("yoti_client_sdk_id not provided.")
        scenario_name = kwargs.pop("yoti_scenario_name")
        if scenario_name is None:
            raise ValueError("yoti_scenario_name not provided.")
        if scenario_name not in VALID_SCENARIO_NAMES:
            raise ValueError(f"Got yoti_scenario_name={scenario_name}, expected one of {VALID_SCENARIO_NAMES}.")
        super().__init__(**kwargs)
        self._yoti_button = YOTI_BUTTON_SCHEMA.format(scenario_id=scenario_id, client_sdk_id=client_sdk_id, scenario_name=scenario_name)
        self._scenario_name = scenario_name
        self._db = {}  # temporary db mock

    @property
    def db(self) -> Dict[str, Dict[str, str]]:
        """Get db."""
        return self._db

    @property
    def yoti_button(self) -> bytes:
        """Get yoti button."""
        return self._yoti_button.encode("utf-8")

    @property
    def success_html(self) -> bytes:
        """Get success html."""
        return SUCCESS.encode("utf-8")

    @property
    def failure_html(self) -> bytes:
        """Get success html."""
        return FAILURE.encode("utf-8")

    @staticmethod
    def info_html(info: Dict[str, str]) -> bytes:
        """Get no_address html."""
        return INFO.format(info=info).encode("utf-8")

    @property
    def scenario_name(self) -> str:
        """Get scenario name."""
        return self._scenario_name

    @property
    def yoti_sdk_dotted_path(self) -> str:
        """Get dotted path for yoti sdk call."""
        return "get_attribute" if self.scenario_name == "age" else ""

    @property
    def yoti_sdk_args(self) -> Tuple[str, ...]:
        """Get args for yoti sdk call."""
        return ("age_over:18",) if self.scenario_name == "age" else ("",)
