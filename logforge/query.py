from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------
# TOKENS
# ---------------------------------------------------------

TOKEN_PATTERN = re.compile(
    r"""
    \s*
    (
        >=
        | <=
        | !=
        | =
        | >
        | <
        | \(
        | \)
        | AND\b
        | OR\b
        | NOT\b
        | "(?:\\.|[^"])*"
        | '(?:\\.|[^'])*'
        | \d+\.\d+
        | \d+
        | [A-Za-z_][A-Za-z0-9_]*
    )
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class Token:
    type: str
    value: str


class QueryLexer:

    def tokenize(self, text: str) -> list[Token]:
        tokens: list[Token] = []
        position = 0

        while position < len(text):

            match = TOKEN_PATTERN.match(
                text,
                position,
            )

            if not match:
                raise ValueError(
                    f"Unexpected character at position "
                    f"{position}: {text[position]!r}"
                )

            value = match.group(1)
            position = match.end()

            if value in {"=", "!=", ">", "<", ">=", "<="}:
                token_type = "OP"

            elif value == "(":
                token_type = "LPAREN"

            elif value == ")":
                token_type = "RPAREN"

            elif value in {"AND", "OR", "NOT"}:
                token_type = value

            elif (
                value.startswith('"')
                or value.startswith("'")
            ):
                token_type = "STRING"

            elif re.fullmatch(r"\d+\.\d+", value):
                token_type = "FLOAT"

            elif value.isdigit():
                token_type = "INTEGER"

            else:
                token_type = "IDENTIFIER"

            tokens.append(
                Token(token_type, value)
            )

        tokens.append(
            Token("EOF", "")
        )

        return tokens


# ---------------------------------------------------------
# AST
# ---------------------------------------------------------

@dataclass(frozen=True)
class Comparison:
    field: str
    operator: str
    value: Any


@dataclass(frozen=True)
class And:
    left: Any
    right: Any


@dataclass(frozen=True)
class Or:
    left: Any
    right: Any


@dataclass(frozen=True)
class Not:
    expression: Any


# ---------------------------------------------------------
# PARSER
# ---------------------------------------------------------

class QueryParser:

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.position = 0

    def current(self) -> Token:
        return self.tokens[self.position]

    def advance(self) -> Token:
        token = self.current()
        self.position += 1
        return token

    def expect(self, token_type: str) -> Token:
        token = self.current()

        if token.type != token_type:
            raise ValueError(
                f"Expected {token_type}, "
                f"got {token.type}"
            )

        return self.advance()

    def parse(self) -> Any:
        expression = self.parse_or()

        self.expect("EOF")

        return expression

    def parse_or(self) -> Any:
        expression = self.parse_and()

        while self.current().type == "OR":
            self.advance()

            expression = Or(
                expression,
                self.parse_and(),
            )

        return expression

    def parse_and(self) -> Any:
        expression = self.parse_not()

        while self.current().type == "AND":
            self.advance()

            expression = And(
                expression,
                self.parse_not(),
            )

        return expression

    def parse_not(self) -> Any:
        if self.current().type == "NOT":
            self.advance()

            return Not(
                self.parse_not()
            )

        return self.parse_primary()

    def parse_primary(self) -> Any:

        if self.current().type == "LPAREN":
            self.advance()

            expression = self.parse_or()

            self.expect("RPAREN")

            return expression

        return self.parse_comparison()

    def parse_comparison(self) -> Comparison:

        field = self.expect(
            "IDENTIFIER"
        ).value

        operator = self.expect(
            "OP"
        ).value

        value_token = self.advance()

        if value_token.type == "INTEGER":
            value = int(value_token.value)

        elif value_token.type == "FLOAT":
            value = float(value_token.value)

        elif value_token.type == "STRING":
            value = value_token.value[1:-1]

        elif value_token.type == "IDENTIFIER":

            if value_token.value == "true":
                value = True

            elif value_token.value == "false":
                value = False

            elif value_token.value == "null":
                value = None

            else:
                value = value_token.value

        else:
            raise ValueError(
                f"Expected comparison value, "
                f"got {value_token.type}"
            )

        return Comparison(
            field=field,
            operator=operator,
            value=value,
        )


def parse_query(text: str) -> Any:
    lexer = QueryLexer()
    tokens = lexer.tokenize(text)

    parser = QueryParser(tokens)

    return parser.parse()