package com.carcare.config;

import org.apache.ibatis.session.SqlSessionFactory;
import org.apache.ibatis.type.TypeHandler;
import org.mybatis.spring.SqlSessionFactoryBean;
import org.mybatis.spring.SqlSessionTemplate;
import org.mybatis.spring.annotation.MapperScan;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.io.support.PathMatchingResourcePatternResolver;

import javax.sql.DataSource;
import java.sql.CallableStatement;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.UUID;

@Configuration
@MapperScan("com.carcare.domain")
public class MyBatisConfig {

    @Bean
    public SqlSessionFactory sqlSessionFactory(DataSource dataSource) throws Exception {
        SqlSessionFactoryBean factoryBean = new SqlSessionFactoryBean();
        factoryBean.setDataSource(dataSource);
        factoryBean.setMapperLocations(
            new PathMatchingResourcePatternResolver().getResources("classpath:mybatis/mapper/**/*.xml")
        );
        factoryBean.setTypeAliasesPackage("com.carcare.domain.*.entity");
        
        // MyBatis 설정
        org.apache.ibatis.session.Configuration configuration = new org.apache.ibatis.session.Configuration();
        configuration.setMapUnderscoreToCamelCase(true);
        configuration.setCacheEnabled(true);
        configuration.setLazyLoadingEnabled(true);
        configuration.setUseGeneratedKeys(true);
        configuration.setDefaultExecutorType(org.apache.ibatis.session.ExecutorType.SIMPLE);
        
        // UUID TypeHandler 등록
        configuration.getTypeHandlerRegistry().register(UUID.class, new UuidTypeHandler());
        
        factoryBean.setConfiguration(configuration);
        
        return factoryBean.getObject();
    }

    @Bean
    public SqlSessionTemplate sqlSessionTemplate(SqlSessionFactory sqlSessionFactory) {
        return new SqlSessionTemplate(sqlSessionFactory);
    }
    
    /**
     * UUID TypeHandler for MyBatis
     */
    public static class UuidTypeHandler implements TypeHandler<UUID> {
        
        @Override
        public void setParameter(PreparedStatement ps, int i, UUID parameter, org.apache.ibatis.type.JdbcType jdbcType) throws SQLException {
            if (parameter == null) {
                ps.setString(i, null);
            } else {
                ps.setString(i, parameter.toString());
            }
        }

        @Override
        public UUID getResult(ResultSet rs, String columnName) throws SQLException {
            String value = rs.getString(columnName);
            return value != null ? UUID.fromString(value) : null;
        }

        @Override
        public UUID getResult(ResultSet rs, int columnIndex) throws SQLException {
            String value = rs.getString(columnIndex);
            return value != null ? UUID.fromString(value) : null;
        }

        @Override
        public UUID getResult(CallableStatement cs, int columnIndex) throws SQLException {
            String value = cs.getString(columnIndex);
            return value != null ? UUID.fromString(value) : null;
        }
    }
} 