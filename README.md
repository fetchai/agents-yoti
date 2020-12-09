# agents-yoti

A repo to explore integrating the AEA framework with Yoti (https://www.yoti.com)


## Running the Demo:

``` bash
aea -s fetch fetchai/yoti_org
cd yoti_org
```

Add the `.env` file:
``` bash
cp ../.env .env
```

``` bash
aea -s run
```

## Demo UML:

![demo uml](./diagram.svg)

<!-- Note left of Alice's Agent: Alice wants\nsomething from Bob
Alice's Agent->Bob's Agent: CFP
Bob's Agent->Alice's Agent: Proposal
Alice's Agent->Bob's Agent: Accept
Note left of Bob's Agent: Bob's Agent needs\nto verify Alice's age
Bob's Agent->Fetch.ai Yoti Agent: Request to verify\nAlice is over 18
Fetch.ai Yoti Agent->Bob's Agent: Here's a link for Alice
Bob's Agent->Alice's Agent: Verify your age\nwith this link
Alice's Agent->Alice: Verify yourself with this link
Alice->Fetch.ai Yoti Agent: Requests Yoti button
Note left of Alice: Yoti flow\n(see image below)
Fetch.ai Yoti Agent->Bob's Agent: Confirm Alice is over 18
Bob's Agent->Alice's Agent: Match Accept
Note right of Alice's Agent: Transaction settlement
Alice's Agent->Bob's Agent: Transaction digest
Bob's Agent->Alice's Agent: Purchased goods/services
 -->

The Yoti flow follows:
![yoti uml](https://github.com/getyoti/yoti-python-sdk/blob/master/login_flow.png)


## Development

Install a new development environment with
``` bash
make new_env
```

Enter shell
``` bash
pipenv shell
```

Install development dependencies
``` bash
make install_env
```

Some linters are available
``` bash
make lint
make static
make security
```
