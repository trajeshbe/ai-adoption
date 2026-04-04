"""Add agents, chat_sessions, chat_messages, and inference_costs tables.

Revision ID: 002
Revises: 001
Create Date: 2026-04-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Agents table ─────────────────────────────────────────────────
    op.create_table(
        "agents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column(
            "agent_type",
            sa.String(50),
            nullable=False,
            comment="WEATHER, QUIZ, RAG, CUSTOM",
        ),
        sa.Column("instructions", sa.Text(), nullable=False, server_default=""),
        sa.Column("model", sa.String(128), server_default="qwen2.5:1.5b"),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ── Chat sessions table ──────────────────────────────────────────
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "agent_id",
            sa.Uuid(),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(512), server_default="New Chat"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_chat_sessions_agent_id", "chat_sessions", ["agent_id"]
    )
    op.create_index(
        "ix_chat_sessions_updated_at", "chat_sessions", ["updated_at"]
    )

    # ── Chat messages table ──────────────────────────────────────────
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(20),
            nullable=False,
            comment="user, assistant, system, tool",
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "tool_calls",
            sa.JSON(),
            nullable=True,
            comment="JSON array of {tool_name, arguments, result}",
        ),
        sa.Column(
            "cost_usd",
            sa.Float(),
            nullable=True,
            comment="Cost of this inference in USD",
        ),
        sa.Column(
            "latency_ms",
            sa.Float(),
            nullable=True,
            comment="End-to-end latency in milliseconds",
        ),
        sa.Column("model", sa.String(128), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_chat_messages_session_id", "chat_messages", ["session_id"]
    )
    op.create_index(
        "ix_chat_messages_created_at", "chat_messages", ["created_at"]
    )

    # ── Inference costs table ────────────────────────────────────────
    op.create_table(
        "inference_costs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("total_cost_usd", sa.Float(), nullable=False),
        sa.Column(
            "agent_type",
            sa.String(50),
            nullable=True,
            comment="Which agent type generated this cost",
        ),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_inference_costs_created_at", "inference_costs", ["created_at"]
    )
    op.create_index(
        "ix_inference_costs_model", "inference_costs", ["model"]
    )

    # ── Seed default agents ──────────────────────────────────────────
    op.execute("""
        INSERT INTO agents (id, name, agent_type, instructions, model) VALUES
        (
            '00000000-0000-0000-0000-000000000001',
            'Movie Quiz Bot',
            'QUIZ',
            'You are a fun movie trivia quiz bot. When the user asks about movies, provide interesting facts and trivia. Engage them with quiz-style questions.',
            'qwen2.5:1.5b'
        ),
        (
            '00000000-0000-0000-0000-000000000002',
            'Weather Agent',
            'WEATHER',
            'You are a helpful weather assistant. When the user asks about weather in a city, use the get_weather tool to fetch real-time data and present it in a clear, friendly format.',
            'qwen2.5:1.5b'
        ),
        (
            '00000000-0000-0000-0000-000000000003',
            'Document Assistant',
            'RAG',
            'You are a document assistant. Use the search_documents tool to find relevant information from the uploaded knowledge base, then answer the user''s question based on the retrieved context.',
            'qwen2.5:1.5b'
        )
        ON CONFLICT (id) DO NOTHING
    """)


def downgrade() -> None:
    op.drop_index("ix_inference_costs_model", table_name="inference_costs")
    op.drop_index("ix_inference_costs_created_at", table_name="inference_costs")
    op.drop_table("inference_costs")
    op.drop_index("ix_chat_messages_created_at", table_name="chat_messages")
    op.drop_index("ix_chat_messages_session_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("ix_chat_sessions_updated_at", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_agent_id", table_name="chat_sessions")
    op.drop_table("chat_sessions")
    op.drop_table("agents")
