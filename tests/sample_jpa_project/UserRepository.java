package com.example.repository;

import com.example.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface UserRepository extends JpaRepository<User, Long> {
    
    // Method queries
    Optional<User> findByUsername(String username);
    
    Optional<User> findByEmail(String email);
    
    List<User> findByIsActiveTrue();
    
    List<User> findByFirstNameContainingIgnoreCase(String firstName);
    
    List<User> findByLastNameContainingIgnoreCase(String lastName);
    
    List<User> findByFirstNameAndLastName(String firstName, String lastName);
    
    long countByIsActiveTrue();
    
    boolean existsByUsername(String username);
    
    boolean existsByEmail(String email);
    
    // Custom JPQL queries
    @Query("SELECT u FROM User u WHERE u.isActive = true AND u.createdAt >= :since")
    List<User> findActiveUsersSince(@Param("since") java.time.LocalDateTime since);
    
    @Query("SELECT u FROM User u WHERE u.firstName LIKE %:name% OR u.lastName LIKE %:name%")
    List<User> findUsersByNameContaining(@Param("name") String name);
    
    // Native SQL queries
    @Query(value = "SELECT * FROM users WHERE is_active = true ORDER BY created_at DESC LIMIT :limit", nativeQuery = true)
    List<User> findRecentActiveUsers(@Param("limit") int limit);
    
    @Query(value = "SELECT COUNT(*) FROM users WHERE created_at >= :since", nativeQuery = true)
    long countUsersCreatedSince(@Param("since") java.time.LocalDateTime since);
    
    // Modifying queries
    @Query("UPDATE User u SET u.isActive = false WHERE u.id = :userId")
    void deactivateUser(@Param("userId") Long userId);
    
    @Query("DELETE FROM User u WHERE u.isActive = false AND u.createdAt < :before")
    void deleteInactiveUsersBefore(@Param("before") java.time.LocalDateTime before);
}
