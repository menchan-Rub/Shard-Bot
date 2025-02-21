const { Role } = require('../models/role');
const { AuditLog } = require('../models/audit_log');

class RolesController {
  static async getRoles(req, res) {
    try {
      const { guildId } = req.params;
      const { search, page = 1, limit = 50 } = req.query;

      const query = { guildId };
      if (search) {
        query.name = { $regex: search, $options: 'i' };
      }

      const skip = (page - 1) * limit;
      
      const [roles, total] = await Promise.all([
        Role.find(query)
          .sort({ position: -1 })
          .skip(skip)
          .limit(parseInt(limit))
          .select('-__v'),
        Role.countDocuments(query)
      ]);

      // Discord APIから最新のロール情報を取得して同期
      const discordRoles = await req.discord.getGuildRoles(guildId);
      await Role.syncFromDiscord(guildId, discordRoles);

      res.json({
        roles,
        total,
        page: parseInt(page),
        totalPages: Math.ceil(total / limit)
      });
    } catch (error) {
      res.status(500).json({ error: 'Failed to get roles' });
    }
  }

  static async createRole(req, res) {
    try {
      const { guildId } = req.params;
      const {
        name,
        color,
        hoist,
        mentionable,
        permissions,
        position,
        reason,
        moderatorId
      } = req.body;

      // Discord APIでロールを作成
      const discordRole = await req.discord.createGuildRole(guildId, {
        name,
        color,
        hoist,
        mentionable,
        permissions,
        position,
        reason
      });

      // データベースにロールを保存
      const role = await Role.create({
        guildId,
        roleId: discordRole.id,
        name: discordRole.name,
        color: discordRole.color.toString(16).padStart(6, '0'),
        position: discordRole.position,
        permissions: discordRole.permissions.toArray(),
        mentionable: discordRole.mentionable,
        hoist: discordRole.hoist,
        managed: discordRole.managed
      });

      // 監査ログに記録
      await AuditLog.create({
        guildId,
        actionType: 'roleCreate',
        userId: moderatorId,
        targetId: role.roleId,
        reason,
        details: {
          name,
          color,
          permissions
        }
      });

      res.json(role);
    } catch (error) {
      res.status(500).json({ error: 'Failed to create role' });
    }
  }

  static async updateRole(req, res) {
    try {
      const { guildId, roleId } = req.params;
      const {
        name,
        color,
        hoist,
        mentionable,
        permissions,
        position,
        reason,
        moderatorId
      } = req.body;

      const role = await Role.findOne({ guildId, roleId });
      if (!role) {
        return res.status(404).json({ error: 'Role not found' });
      }

      // Discord APIでロールを更新
      const discordRole = await req.discord.updateGuildRole(guildId, roleId, {
        name,
        color,
        hoist,
        mentionable,
        permissions,
        position,
        reason
      });

      // データベースのロールを更新
      role.name = discordRole.name;
      role.color = discordRole.color.toString(16).padStart(6, '0');
      role.position = discordRole.position;
      role.permissions = discordRole.permissions.toArray();
      role.mentionable = discordRole.mentionable;
      role.hoist = discordRole.hoist;
      await role.save();

      // 監査ログに記録
      await AuditLog.create({
        guildId,
        actionType: 'roleUpdate',
        userId: moderatorId,
        targetId: role.roleId,
        reason,
        details: {
          name,
          color,
          permissions
        }
      });

      res.json(role);
    } catch (error) {
      res.status(500).json({ error: 'Failed to update role' });
    }
  }

  static async deleteRole(req, res) {
    try {
      const { guildId, roleId } = req.params;
      const { reason, moderatorId } = req.body;

      const role = await Role.findOne({ guildId, roleId });
      if (!role) {
        return res.status(404).json({ error: 'Role not found' });
      }

      // Discord APIでロールを削除
      await req.discord.deleteGuildRole(guildId, roleId, reason);

      // データベースからロールを削除
      await role.remove();

      // 監査ログに記録
      await AuditLog.create({
        guildId,
        actionType: 'roleDelete',
        userId: moderatorId,
        targetId: role.roleId,
        reason,
        details: {
          name: role.name
        }
      });

      res.json({ message: 'Role deleted successfully' });
    } catch (error) {
      res.status(500).json({ error: 'Failed to delete role' });
    }
  }

  static async getRoleMembers(req, res) {
    try {
      const { guildId, roleId } = req.params;
      const { page = 1, limit = 50 } = req.query;

      const role = await Role.findOne({ guildId, roleId });
      if (!role) {
        return res.status(404).json({ error: 'Role not found' });
      }

      // Discord APIからロールメンバーを取得
      const members = await req.discord.getGuildRoleMembers(guildId, roleId);
      const total = members.length;
      const skip = (page - 1) * limit;

      // ページネーション
      const paginatedMembers = members
        .slice(skip, skip + parseInt(limit))
        .map(member => ({
          id: member.user.id,
          username: member.user.username,
          discriminator: member.user.discriminator,
          avatar: member.user.avatar,
          joinedAt: member.joinedAt
        }));

      res.json({
        members: paginatedMembers,
        total,
        page: parseInt(page),
        totalPages: Math.ceil(total / limit)
      });
    } catch (error) {
      res.status(500).json({ error: 'Failed to get role members' });
    }
  }
}

module.exports = RolesController; 