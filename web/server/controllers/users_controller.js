const { User } = require('../models/user');
const { Warning } = require('../models/warning');
const { AuditLog } = require('../models/audit_log');

class UsersController {
  static async getUsers(req, res) {
    try {
      const { guildId } = req.params;
      const { search, page = 1, limit = 50 } = req.query;

      const query = { guilds: guildId };
      if (search) {
        query.$or = [
          { username: { $regex: search, $options: 'i' } },
          { discordId: { $regex: search, $options: 'i' } }
        ];
      }

      const skip = (page - 1) * limit;
      
      const [users, total] = await Promise.all([
        User.find(query)
          .sort({ username: 1 })
          .skip(skip)
          .limit(parseInt(limit))
          .select('username discordId avatar warnings isBanned lastActive'),
        User.countDocuments(query)
      ]);

      res.json({
        users,
        total,
        page: parseInt(page),
        totalPages: Math.ceil(total / limit)
      });
    } catch (error) {
      res.status(500).json({ error: 'Failed to get users' });
    }
  }

  static async getUserDetails(req, res) {
    try {
      const { guildId, userId } = req.params;

      const user = await User.findOne({
        discordId: userId,
        guilds: guildId
      }).select('-__v');

      if (!user) {
        return res.status(404).json({ error: 'User not found' });
      }

      // 警告履歴を取得
      const warnings = await Warning.find({
        guildId,
        userId: user.discordId
      }).sort({ createdAt: -1 });

      res.json({
        ...user.toJSON(),
        warnings
      });
    } catch (error) {
      res.status(500).json({ error: 'Failed to get user details' });
    }
  }

  static async warnUser(req, res) {
    try {
      const { guildId, userId } = req.params;
      const { reason, moderatorId } = req.body;

      const user = await User.findOne({
        discordId: userId,
        guilds: guildId
      });

      if (!user) {
        return res.status(404).json({ error: 'User not found' });
      }

      // 警告を作成
      const warning = await Warning.create({
        guildId,
        userId: user.discordId,
        moderatorId,
        reason
      });

      // ユーザーの警告カウントを更新
      user.warnings += 1;
      user.warningDates.push(new Date());
      await user.save();

      // 監査ログに記録
      await AuditLog.create({
        guildId,
        actionType: 'warn',
        userId: moderatorId,
        targetId: user.discordId,
        reason,
        details: { warningId: warning._id }
      });

      res.json(warning);
    } catch (error) {
      res.status(500).json({ error: 'Failed to warn user' });
    }
  }

  static async banUser(req, res) {
    try {
      const { guildId, userId } = req.params;
      const { reason, moderatorId, deleteMessageDays = 1 } = req.body;

      const user = await User.findOne({
        discordId: userId,
        guilds: guildId
      });

      if (!user) {
        return res.status(404).json({ error: 'User not found' });
      }

      // ユーザーをBAN
      user.isBanned = true;
      user.bannedAt = new Date();
      await user.save();

      // Discord APIでBANを実行
      await req.discord.banGuildMember(guildId, userId, {
        reason,
        deleteMessageDays
      });

      // 監査ログに記録
      await AuditLog.create({
        guildId,
        actionType: 'ban',
        userId: moderatorId,
        targetId: user.discordId,
        reason
      });

      res.json({ message: 'User banned successfully' });
    } catch (error) {
      res.status(500).json({ error: 'Failed to ban user' });
    }
  }

  static async unbanUser(req, res) {
    try {
      const { guildId, userId } = req.params;
      const { reason, moderatorId } = req.body;

      const user = await User.findOne({
        discordId: userId,
        guilds: guildId
      });

      if (!user) {
        return res.status(404).json({ error: 'User not found' });
      }

      // BANを解除
      user.isBanned = false;
      user.bannedAt = null;
      await user.save();

      // Discord APIでBAN解除を実行
      await req.discord.unbanGuildMember(guildId, userId);

      // 監査ログに記録
      await AuditLog.create({
        guildId,
        actionType: 'unban',
        userId: moderatorId,
        targetId: user.discordId,
        reason
      });

      res.json({ message: 'User unbanned successfully' });
    } catch (error) {
      res.status(500).json({ error: 'Failed to unban user' });
    }
  }

  static async clearWarnings(req, res) {
    try {
      const { guildId, userId } = req.params;
      const { reason, moderatorId } = req.body;

      const user = await User.findOne({
        discordId: userId,
        guilds: guildId
      });

      if (!user) {
        return res.status(404).json({ error: 'User not found' });
      }

      // 警告をクリア
      await Warning.updateMany(
        { guildId, userId: user.discordId },
        { $set: { active: false } }
      );

      // ユーザーの警告カウントをリセット
      user.warnings = 0;
      user.warningDates = [];
      await user.save();

      // 監査ログに記録
      await AuditLog.create({
        guildId,
        actionType: 'clearWarnings',
        userId: moderatorId,
        targetId: user.discordId,
        reason
      });

      res.json({ message: 'Warnings cleared successfully' });
    } catch (error) {
      res.status(500).json({ error: 'Failed to clear warnings' });
    }
  }
}

module.exports = UsersController; 