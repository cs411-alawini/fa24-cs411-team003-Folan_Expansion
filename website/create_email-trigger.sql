-- First run:
DELIMITER $$

-- Create insert trigger
CREATE TRIGGER email_check_before_insert
BEFORE INSERT ON User
FOR EACH ROW
BEGIN
    IF NEW.email IS NULL OR NEW.email NOT LIKE '%@gmail.com' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Email must be a non-null Gmail address.';
    END IF;
END$$

-- Create update trigger
CREATE TRIGGER email_check_before_update
BEFORE UPDATE ON User
FOR EACH ROW
BEGIN
    IF NEW.email IS NULL OR NEW.email NOT LIKE '%@gmail.com' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Email must be a non-null Gmail address.';
    END IF;
END$$

DELIMITER ;

-- Then run this separately to fix existing records:
UPDATE User
SET email = CONCAT(username, '@gmail.com')
WHERE email IS NULL OR email NOT LIKE '%@gmail.com';

-- After confirming everything works, you can drop the triggers:
DROP TRIGGER IF EXISTS email_check_before_insert;
DROP TRIGGER IF EXISTS email_check_before_update;