package com.carcare.common.config;

import com.carcare.domain.notification.entity.NotificationTemplate.NotificationChannel;
import org.apache.ibatis.type.BaseTypeHandler;
import org.apache.ibatis.type.JdbcType;
import org.apache.ibatis.type.MappedJdbcTypes;
import org.apache.ibatis.type.MappedTypes;

import java.sql.CallableStatement;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

/**
 * NotificationChannel enum을 위한 커스텀 TypeHandler
 */
@MappedJdbcTypes(JdbcType.VARCHAR)
@MappedTypes(NotificationChannel.class)
public class NotificationChannelTypeHandler extends BaseTypeHandler<NotificationChannel> {

    @Override
    public void setNonNullParameter(PreparedStatement ps, int i, NotificationChannel parameter, JdbcType jdbcType) throws SQLException {
        ps.setString(i, parameter.name());
    }

    @Override
    public NotificationChannel getNullableResult(ResultSet rs, String columnName) throws SQLException {
        String value = rs.getString(columnName);
        return value == null ? null : NotificationChannel.valueOf(value);
    }

    @Override
    public NotificationChannel getNullableResult(ResultSet rs, int columnIndex) throws SQLException {
        String value = rs.getString(columnIndex);
        return value == null ? null : NotificationChannel.valueOf(value);
    }

    @Override
    public NotificationChannel getNullableResult(CallableStatement cs, int columnIndex) throws SQLException {
        String value = cs.getString(columnIndex);
        return value == null ? null : NotificationChannel.valueOf(value);
    }
} 