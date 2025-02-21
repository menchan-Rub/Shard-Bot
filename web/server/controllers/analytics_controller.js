const { Guild } = require('../models/guild');
const { User } = require('../models/user');
const { AuditLog } = require('../models/audit_log');
const { SpamLog } = require('../models/spam_log');

class AnalyticsController {
  static async getOverview(req, res) {
    try {
      const { guildId } = req.params;
      const guild = await Guild.findOne({ guildId });
      
      if (!guild) {
        return res.status(404).json({ error: 'Guild not found' });
      }

      // 基本的な統計情報を取得
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      const [
        totalUsers,
        activeUsers,
        totalMessages,
        messagesToday,
        totalCommands,
        commandsToday,
        spamDetections,
        raidDetections,
        moderationActions
      ] = await Promise.all([
        User.countDocuments({ guilds: guildId }),
        User.countDocuments({ guilds: guildId, lastActive: { $gte: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000) } }),
        guild.stats.totalMessages,
        guild.dailyStats.find(stat => stat.date.getTime() === today.getTime())?.messages || 0,
        guild.stats.totalCommands,
        guild.dailyStats.find(stat => stat.date.getTime() === today.getTime())?.commands || 0,
        guild.stats.spamDetections,
        guild.stats.raidDetections,
        AuditLog.countDocuments({
          guildId,
          actionType: { $in: ['warn', 'mute', 'kick', 'ban'] },
          createdAt: { $gte: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000) }
        })
      ]);

      // アクティブユーザー率を計算
      const activeUserRate = totalUsers > 0 ? (activeUsers / totalUsers * 100).toFixed(2) : 0;

      res.json({
        totalUsers,
        activeUsers,
        activeUserRate,
        totalMessages,
        messagesToday,
        totalCommands,
        commandsToday,
        spamDetections,
        raidDetections,
        moderationActions
      });
    } catch (error) {
      res.status(500).json({ error: 'Failed to get overview data' });
    }
  }

  static async getActivityData(req, res) {
    try {
      const { guildId } = req.params;
      const { days = 30 } = req.query;

      const guild = await Guild.findOne({ guildId });
      if (!guild) {
        return res.status(404).json({ error: 'Guild not found' });
      }

      const cutoff = new Date();
      cutoff.setDate(cutoff.getDate() - days);

      // 日次統計データを取得
      const dailyStats = guild.dailyStats
        .filter(stat => stat.date >= cutoff)
        .map(stat => ({
          date: stat.date,
          messages: stat.messages,
          commands: stat.commands,
          newMembers: stat.newMembers,
          leftMembers: stat.leftMembers,
          warnings: stat.warnings,
          mutes: stat.mutes,
          kicks: stat.kicks,
          bans: stat.bans,
          spamDetections: stat.spamDetections,
          raidDetections: stat.raidDetections
        }));

      // 日付でソート
      dailyStats.sort((a, b) => a.date - b.date);

      res.json(dailyStats);
    } catch (error) {
      res.status(500).json({ error: 'Failed to get activity data' });
    }
  }

  static async getCommandStats(req, res) {
    try {
      const { guildId } = req.params;
      const { days = 30 } = req.query;

      const cutoff = new Date();
      cutoff.setDate(cutoff.getDate() - days);

      // コマンドの使用統計を集計
      const commandStats = await AuditLog.aggregate([
        {
          $match: {
            guildId,
            actionType: 'command',
            createdAt: { $gte: cutoff }
          }
        },
        {
          $group: {
            _id: '$details.command',
            count: { $sum: 1 }
          }
        },
        {
          $sort: { count: -1 }
        }
      ]);

      res.json(commandStats);
    } catch (error) {
      res.status(500).json({ error: 'Failed to get command stats' });
    }
  }

  static async getModStats(req, res) {
    try {
      const { guildId } = req.params;
      const { days = 30 } = req.query;

      const cutoff = new Date();
      cutoff.setDate(cutoff.getDate() - days);

      // モデレーション行動の統計を集計
      const [modActions, spamDetections] = await Promise.all([
        AuditLog.aggregate([
          {
            $match: {
              guildId,
              actionType: { $in: ['warn', 'mute', 'kick', 'ban'] },
              createdAt: { $gte: cutoff }
            }
          },
          {
            $group: {
              _id: '$actionType',
              count: { $sum: 1 }
            }
          }
        ]),
        SpamLog.aggregate([
          {
            $match: {
              guildId,
              createdAt: { $gte: cutoff }
            }
          },
          {
            $group: {
              _id: '$detectionType',
              count: { $sum: 1 }
            }
          }
        ])
      ]);

      res.json({
        modActions: modActions.reduce((acc, { _id, count }) => {
          acc[_id] = count;
          return acc;
        }, {}),
        spamDetections: spamDetections.reduce((acc, { _id, count }) => {
          acc[_id] = count;
          return acc;
        }, {})
      });
    } catch (error) {
      res.status(500).json({ error: 'Failed to get moderation stats' });
    }
  }

  static async getUserStats(req, res) {
    try {
      const { guildId } = req.params;
      const { days = 30 } = req.query;

      const cutoff = new Date();
      cutoff.setDate(cutoff.getDate() - days);

      // ユーザー関連の統計を集計
      const [newUsers, leftUsers, warnedUsers, bannedUsers] = await Promise.all([
        User.countDocuments({
          guilds: guildId,
          createdAt: { $gte: cutoff }
        }),
        AuditLog.countDocuments({
          guildId,
          actionType: 'member_leave',
          createdAt: { $gte: cutoff }
        }),
        User.countDocuments({
          guilds: guildId,
          warnings: { $gt: 0 },
          'warningDates.0': { $gte: cutoff }
        }),
        User.countDocuments({
          guilds: guildId,
          isBanned: true,
          bannedAt: { $gte: cutoff }
        })
      ]);

      res.json({
        newUsers,
        leftUsers,
        warnedUsers,
        bannedUsers
      });
    } catch (error) {
      res.status(500).json({ error: 'Failed to get user stats' });
    }
  }
}

module.exports = AnalyticsController; 