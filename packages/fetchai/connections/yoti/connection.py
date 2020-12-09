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

"""Scaffold connection and channel."""

import asyncio
import functools
from abc import ABC
from asyncio import Task
from collections import deque
from concurrent.futures._base import Executor
from logging import Logger
from typing import Any, Callable, Deque, Dict, List, Optional, cast

from yoti_python_sdk import Client as YotiClient

from aea.common import Address
from aea.configurations.base import PublicId
from aea.connections.base import Connection, ConnectionStates
from aea.helpers.async_utils import AsyncState
from aea.mail.base import Envelope
from aea.protocols.base import Message
from aea.protocols.dialogue.base import Dialogue

from packages.fetchai.protocols.yoti.dialogues import YotiDialogue
from packages.fetchai.protocols.yoti.dialogues import YotiDialogues as BaseYotiDialogues
from packages.fetchai.protocols.yoti.message import YotiMessage


CONNECTION_ID = PublicId.from_str("fetchai/yoti:0.1.0")


def rgetattr(obj, attr, *args):
    """Recursive getattr."""

    def _getattr(obj, attr):
        return getattr(obj, attr, *args)

    return functools.reduce(_getattr, [obj] + attr.split("."))


class YotiDialogues(BaseYotiDialogues):
    """The dialogues class keeps track of all dialogues."""

    def __init__(self, **kwargs) -> None:
        """
        Initialize dialogues.

        :return: None
        """

        def role_from_first_message(  # pylint: disable=unused-argument
            message: Message, receiver_address: Address
        ) -> Dialogue.Role:
            """Infer the role of the agent from an incoming/outgoing first message

            :param message: an incoming/outgoing first message
            :param receiver_address: the address of the receiving agent
            :return: The role of the agent
            """
            # The yoti connection maintains the dialogue on behalf of the yoti server
            return YotiDialogue.Role.YOTI_SERVER

        BaseYotiDialogues.__init__(
            self,
            self_address=str(CONNECTION_ID),
            role_from_first_message=role_from_first_message,
            **kwargs,
        )


class YotiRequestDispatcher(ABC):
    """Class for a request dispatcher."""

    def __init__(
        self,
        client: YotiClient,
        logger: Logger,
        connection_state: AsyncState,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        executor: Optional[Executor] = None,
    ):
        """
        Initialize the request dispatcher.

        :param loop: the asyncio loop.
        :param executor: an executor.
        """
        self.connection_state = connection_state
        self.loop = loop if loop is not None else asyncio.get_event_loop()
        self.executor = executor
        self.logger = logger
        self.client = client
        self.dialogues = YotiDialogues()

    async def run_async(
        self, func: Callable[[Any], Task], message: YotiMessage, dialogue: YotiDialogue,
    ):
        """
        Run a function in executor.

        :param func: the function to execute.
        :param args: the arguments to pass to the function.
        :return: the return value of the function.
        """
        try:
            response = await self.loop.run_in_executor(
                self.executor, func, message, dialogue
            )
            return response
        except Exception as e:  # pylint: disable=broad-except
            return self.get_error_message(e, message, dialogue)

    def dispatch(self, envelope: Envelope) -> Task:
        """
        Dispatch the request to the right sender handler.

        :param envelope: the envelope.
        :return: an awaitable.
        """
        if not isinstance(envelope.message, Message):  # pragma: nocover
            raise ValueError("Yoti connection expects non-serialized messages.")
        message = cast(YotiMessage, envelope.message)
        dialogue = cast(Optional[YotiDialogue], self.dialogues.update(message))
        if dialogue is None:
            raise ValueError(  # pragma: nocover
                "No dialogue created. Message={} not valid.".format(message)
            )
        performative = message.performative
        handler = self.get_handler(performative.value)
        return self.loop.create_task(self.run_async(handler, message, dialogue))

    def get_handler(self, performative: str) -> Callable[[Any], Task]:
        """
        Get the handler method, given the message performative.

        :param performative_name: the message performative.
        :return: the method that will send the request.
        """
        handler = getattr(self, performative, None)
        if handler is None:
            raise Exception("Performative not recognized.")
        return handler

    def get_profile(self, message: YotiMessage, dialogue: YotiDialogue) -> YotiMessage:
        """
        Send the request 'get_request'.

        :param message: the Yoti message
        :param dialogue: the Yoti dialogue
        :return: None
        """
        activity_details = self.client.get_activity_details(message.token)
        if activity_details is None:
            response = self.get_error_message(
                ValueError("No activity_details returned"), message, dialogue
            )
            return response
        try:
            remember_me_id = activity_details.user_id
            profile = activity_details.profile
            callable_ = rgetattr(profile, message.dotted_path, *message.args)
            if len(message.args) != 0:
                intermediate = callable_(*message.args)
            else:
                intermediate = callable_
            result = {
                "remember_me_id": remember_me_id,
                "name": intermediate.name,
                "value": intermediate.value,
                "sources": ",".join([source.value for source in intermediate.sources]),
                "verifiers": ",".join(
                    [verifier.value for verifier in intermediate.verifiers]
                ),
            }
            response = cast(
                YotiMessage,
                dialogue.reply(
                    performative=YotiMessage.Performative.PROFILE,
                    target_message=message,
                    info=result,
                ),
            )
        except Exception as e:  # pylint: disable=broad-except
            response = self.get_error_message(e, message, dialogue)
        return response

    @staticmethod
    def get_error_message(
        e: Exception, message: YotiMessage, dialogue: YotiDialogue,
    ) -> YotiMessage:
        """
        Build an error message.

        :param e: the exception
        :param message: the received message.
        :param dialogue: the dialogue.
        :return: an error message response.
        """
        response = cast(
            YotiMessage,
            dialogue.reply(
                performative=YotiMessage.Performative.ERROR,
                target_message=message,
                error_code=500,
                error_msg=str(e),
            ),
        )
        return response


class YotiConnection(Connection):
    """Proxy to the functionality of the SDK or API."""

    connection_id = PublicId.from_str("fetchai/yoti:0.1.0")

    def __init__(self, **kwargs):
        """
        Initialize a connection to an SDK or API.

        :param configuration: the connection configuration.
        :param crypto_store: object to access the connection crypto objects.
        :param identity: the identity object.
        """
        super().__init__(**kwargs)  # pragma: no cover
        yoti_client_sdk_id = cast(
            Optional[str], self.configuration.config.get("yoti_client_sdk_id")
        )
        yoti_key_file_path = cast(
            Optional[str], self.configuration.config.get("yoti_key_file_path")
        )
        if yoti_client_sdk_id is None or yoti_key_file_path is None:
            raise ValueError("Missing configuration.")
        self._client = YotiClient(yoti_client_sdk_id, yoti_key_file_path)
        self._dispatcher: Optional[YotiRequestDispatcher] = None
        self._event_new_receiving_task: Optional[asyncio.Event] = None

        self.receiving_tasks: List[asyncio.Future] = []
        self.task_to_request: Dict[asyncio.Future, Envelope] = {}
        self.done_tasks: Deque[asyncio.Future] = deque()

    @property
    def event_new_receiving_task(self) -> asyncio.Event:
        """Get the event to notify the 'receive' method of new receiving tasks."""
        if self._event_new_receiving_task is None:
            raise ValueError("Call connect first!")
        return self._event_new_receiving_task

    async def connect(self) -> None:
        """
        Set up the connection.

        In the implementation, remember to update 'connection_status' accordingly.
        """
        if self.is_connected:  # pragma: nocover
            return
        self._state.set(ConnectionStates.connecting)
        self._dispatcher = YotiRequestDispatcher(
            self._client, self.logger, self._state, loop=self.loop,
        )
        self._event_new_receiving_task = asyncio.Event(loop=self.loop)
        self._state.set(ConnectionStates.connected)

    async def disconnect(self) -> None:
        """
        Tear down the connection.

        In the implementation, remember to update 'connection_status' accordingly.
        """
        if self.is_disconnected:  # pragma: nocover
            return

        self._state.set(ConnectionStates.disconnecting)

        for task in self.receiving_tasks:
            if not task.cancelled():  # pragma: nocover
                task.cancel()
        self._dispatcher = None
        self._event_new_receiving_task = None

        self._state.set(ConnectionStates.disconnected)

    async def send(self, envelope: "Envelope") -> None:
        """
        Send an envelope.

        :param envelope: the envelope to send.
        :return: None
        """
        task = self._schedule_request(envelope)
        self.receiving_tasks.append(task)
        self.task_to_request[task] = envelope
        self.event_new_receiving_task.set()

    async def receive(self, *args, **kwargs) -> Optional["Envelope"]:
        """
        Receive an envelope. Blocking.

        :return: the envelope received, or None.
        """
        # if there are done tasks, return the result
        if len(self.done_tasks) > 0:  # pragma: nocover
            done_task = self.done_tasks.pop()
            return self._handle_done_task(done_task)

        if len(self.receiving_tasks) == 0:
            self.event_new_receiving_task.clear()
            await self.event_new_receiving_task.wait()

        # wait for completion of at least one receiving task
        done, _ = await asyncio.wait(
            self.receiving_tasks, return_when=asyncio.FIRST_COMPLETED
        )

        # pick one done task
        done_task = done.pop()

        # update done tasks
        self.done_tasks.extend([*done])

        return self._handle_done_task(done_task)

    def _schedule_request(self, envelope: Envelope) -> Task:
        """
        Schedule a ledger API request.

        :param envelope: the message.
        :return: None
        """
        if self._dispatcher is None:  # pragma: nocover
            raise ValueError("No dispatcher set.")
        task = self._dispatcher.dispatch(envelope)
        return task

    def _handle_done_task(self, task: asyncio.Future) -> Optional[Envelope]:
        """
        Process a done receiving task.

        :param task: the done task.
        :return: the reponse envelope.
        """
        request = self.task_to_request.pop(task)
        self.receiving_tasks.remove(task)
        response_message: Optional[Message] = task.result()

        response_envelope = None
        if response_message is not None:
            response_envelope = Envelope(
                to=request.sender,
                sender=request.to,
                protocol_id=response_message.protocol_id,
                message=response_message,
                context=request.context,
            )
        return response_envelope
