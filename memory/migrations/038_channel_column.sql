-- Add channel column to whatsapp_messages for multi-channel support
ALTER TABLE whatsapp_messages ADD COLUMN IF NOT EXISTS channel TEXT DEFAULT 'whatsapp';
CREATE INDEX IF NOT EXISTS idx_messages_channel ON whatsapp_messages(channel);
