const { Channel } = require('../models/channel');
const { AuditLog } = require('../models/audit_log');

class ChannelsController {
  static async getChannels(req, res) {
    try {
      const { guildId } = req.params;
      const { type, search, page = 1, limit = 50 } = req.query;

      const query = { guildId };
      if (type) {
        query.type = type;
      }
      if (search) {
        query.name = { $regex: search, $options: 'i' };
      }

      const skip = (page - 1) * limit;
      
      const [channels, total] = await Promise.all([
        Channel.find(query)
          .sort({ position: 1 })
          .skip(skip)
          .limit(parseInt(limit))
          .select('-__v'),
        Channel.countDocuments(query)
      ]);

      // Discord APIから最新のチャンネル情報を取得して同期
      const discordChannels = await req.discord.getGuildChannels(guildId);
      await Channel.syncFromDiscord(guildId, discordChannels);

      res.json({
        channels,
        total,
        page: parseInt(page),
        totalPages: Math.ceil(total / limit)
      });
    } catch (error) {
      res.status(500).json({ error: 'Failed to get channels' });
    }
  }

  static async createChannel(req, res) {
    try {
      const { guildId } = req.params;
      const {
        name,
        type,
        topic,
        nsfw,
        bitrate,
        userLimit,
        parentId,
        position,
        permissionOverwrites,
        reason,
        moderatorId
      } = req.body;

      // Discord APIでチャンネルを作成
      const discordChannel = await req.discord.createGuildChannel(guildId, {
        name,
        type,
        topic,
        nsfw,
        bitrate,
        userLimit,
        parent: parentId,
        position,
        permissionOverwrites,
        reason
      });

      // データベースにチャンネルを保存
      const channel = await Channel.create({
        guildId,
        channelId: discordChannel.id,
        name: discordChannel.name,
        type: discordChannel.type,
        topic: discordChannel.topic,
        nsfw: discordChannel.nsfw,
        bitrate: discordChannel.bitrate,
        userLimit: discordChannel.userLimit,
        parentId: discordChannel.parentId,
        position: discordChannel.position,
        permissions: discordChannel.permissionOverwrites.cache.map(perm => ({
          roleId: perm.type === 'role' ? perm.id : null,
          allow: perm.allow.toArray(),
          deny: perm.deny.toArray()
        }))
      });

      // 監査ログに記録
      await AuditLog.create({
        guildId,
        actionType: 'channelCreate',
        userId: moderatorId,
        targetId: channel.channelId,
        reason,
        details: {
          name,
          type,
          topic
        }
      });

      res.json(channel);
    } catch (error) {
      res.status(500).json({ error: 'Failed to create channel' });
    }
  }

  static async updateChannel(req, res) {
    try {
      const { guildId, channelId } = req.params;
      const {
        name,
        topic,
        nsfw,
        bitrate,
        userLimit,
        parentId,
        position,
        permissionOverwrites,
        reason,
        moderatorId
      } = req.body;

      const channel = await Channel.findOne({ guildId, channelId });
      if (!channel) {
        return res.status(404).json({ error: 'Channel not found' });
      }

      // Discord APIでチャンネルを更新
      const discordChannel = await req.discord.updateGuildChannel(guildId, channelId, {
        name,
        topic,
        nsfw,
        bitrate,
        userLimit,
        parent: parentId,
        position,
        permissionOverwrites,
        reason
      });

      // データベースのチャンネルを更新
      channel.name = discordChannel.name;
      channel.topic = discordChannel.topic;
      channel.nsfw = discordChannel.nsfw;
      channel.bitrate = discordChannel.bitrate;
      channel.userLimit = discordChannel.userLimit;
      channel.parentId = discordChannel.parentId;
      channel.position = discordChannel.position;
      channel.permissions = discordChannel.permissionOverwrites.cache.map(perm => ({
        roleId: perm.type === 'role' ? perm.id : null,
        allow: perm.allow.toArray(),
        deny: perm.deny.toArray()
      }));
      await channel.save();

      // 監査ログに記録
      await AuditLog.create({
        guildId,
        actionType: 'channelUpdate',
        userId: moderatorId,
        targetId: channel.channelId,
        reason,
        details: {
          name,
          topic,
          nsfw
        }
      });

      res.json(channel);
    } catch (error) {
      res.status(500).json({ error: 'Failed to update channel' });
    }
  }

  static async deleteChannel(req, res) {
    try {
      const { guildId, channelId } = req.params;
      const { reason, moderatorId } = req.body;

      const channel = await Channel.findOne({ guildId, channelId });
      if (!channel) {
        return res.status(404).json({ error: 'Channel not found' });
      }

      // Discord APIでチャンネルを削除
      await req.discord.deleteGuildChannel(guildId, channelId, reason);

      // データベースからチャンネルを削除
      await channel.remove();

      // 監査ログに記録
      await AuditLog.create({
        guildId,
        actionType: 'channelDelete',
        userId: moderatorId,
        targetId: channel.channelId,
        reason,
        details: {
          name: channel.name,
          type: channel.type
        }
      });

      res.json({ message: 'Channel deleted successfully' });
    } catch (error) {
      res.status(500).json({ error: 'Failed to delete channel' });
    }
  }

  static async getCategories(req, res) {
    try {
      const { guildId } = req.params;

      const categories = await Channel.find({
        guildId,
        type: 'GUILD_CATEGORY'
      }).sort({ position: 1 });

      res.json(categories);
    } catch (error) {
      res.status(500).json({ error: 'Failed to get categories' });
    }
  }

  static async updatePermissions(req, res) {
    try {
      const { guildId, channelId } = req.params;
      const { roleId, allow, deny, reason, moderatorId } = req.body;

      const channel = await Channel.findOne({ guildId, channelId });
      if (!channel) {
        return res.status(404).json({ error: 'Channel not found' });
      }

      // Discord APIで権限を更新
      await req.discord.updateChannelPermissions(guildId, channelId, roleId, {
        allow,
        deny,
        reason
      });

      // データベースの権限を更新
      const permIndex = channel.permissions.findIndex(p => p.roleId === roleId);
      if (permIndex !== -1) {
        channel.permissions[permIndex] = { roleId, allow, deny };
      } else {
        channel.permissions.push({ roleId, allow, deny });
      }
      await channel.save();

      // 監査ログに記録
      await AuditLog.create({
        guildId,
        actionType: 'channelPermissionUpdate',
        userId: moderatorId,
        targetId: channel.channelId,
        reason,
        details: {
          roleId,
          allow,
          deny
        }
      });

      res.json(channel);
    } catch (error) {
      res.status(500).json({ error: 'Failed to update permissions' });
    }
  }
}

module.exports = ChannelsController; 