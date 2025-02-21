const { Settings } = require('../models/settings');
const { Guild } = require('../models/guild');

class SettingsController {
  static async getSettings(req, res) {
    try {
      const { guildId } = req.params;
      const settings = await Settings.findOne({ guildId });
      
      if (!settings) {
        return res.status(404).json({ error: 'Settings not found' });
      }

      res.json(settings);
    } catch (error) {
      res.status(500).json({ error: 'Failed to get settings' });
    }
  }

  static async updateSettings(req, res) {
    try {
      const { guildId } = req.params;
      const updateData = req.body;

      const settings = await Settings.findOneAndUpdate(
        { guildId },
        { $set: updateData },
        { new: true, upsert: true }
      );

      // ギルド設定も更新
      await Guild.findOneAndUpdate(
        { guildId },
        { $set: {
          prefix: updateData.prefix,
          language: updateData.language,
          modRoleId: updateData.modRoleId,
          adminRoleId: updateData.adminRoleId,
          logChannelId: updateData.logChannelId,
          welcomeChannelId: updateData.welcomeChannelId,
          welcomeMessage: updateData.welcomeMessage,
          leaveMessage: updateData.leaveMessage,
          spamProtection: updateData.spamProtection,
          raidProtection: updateData.raidProtection,
        }},
        { new: true, upsert: true }
      );

      res.json(settings);
    } catch (error) {
      res.status(500).json({ error: 'Failed to update settings' });
    }
  }

  static async getGuildRoles(req, res) {
    try {
      const { guildId } = req.params;
      const guild = await Guild.findOne({ guildId });
      
      if (!guild) {
        return res.status(404).json({ error: 'Guild not found' });
      }

      // Discordから最新のロール情報を取得
      const roles = await req.discord.getGuildRoles(guildId);
      res.json(roles);
    } catch (error) {
      res.status(500).json({ error: 'Failed to get guild roles' });
    }
  }

  static async getGuildChannels(req, res) {
    try {
      const { guildId } = req.params;
      const guild = await Guild.findOne({ guildId });
      
      if (!guild) {
        return res.status(404).json({ error: 'Guild not found' });
      }

      // Discordから最新のチャンネル情報を取得
      const channels = await req.discord.getGuildChannels(guildId);
      res.json(channels);
    } catch (error) {
      res.status(500).json({ error: 'Failed to get guild channels' });
    }
  }

  static async resetSettings(req, res) {
    try {
      const { guildId } = req.params;
      
      await Settings.findOneAndDelete({ guildId });
      const defaultSettings = await Settings.create({
        guildId,
        prefix: '!',
        language: 'ja',
        spamProtection: true,
        raidProtection: true,
      });

      res.json(defaultSettings);
    } catch (error) {
      res.status(500).json({ error: 'Failed to reset settings' });
    }
  }
}

module.exports = SettingsController; 