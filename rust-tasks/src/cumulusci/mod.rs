use std::alloc::{alloc, Layout};

pub trait Freeze<T> {
    fn freeze(&self, cumulusci: &CumulusCI) -> T;
}

#[repr(C)]
pub struct CumulusCI {}

impl CumulusCI {
    pub fn get_access_token(&self) -> String {
        let (ptr, length) = unsafe { get_access_token() };
        unsafe { String::from_raw_parts(ptr, length as usize, length as usize) }
    }

    pub fn get_instance_url(&self) -> String {
        let (ptr, length) = unsafe { get_instance_url() };
        unsafe { String::from_raw_parts(ptr, length as usize, length as usize) }
    }
}

#[no_mangle]
pub extern "C" fn allocate(size: u32) -> *mut u8 {
    // Alignment must be 1 for `String::from_raw_parts()` to be safe.
    unsafe { alloc(Layout::from_size_align(size as usize, 1).unwrap()) }
}

#[no_mangle]
pub extern "C" fn deallocate(ptr: *mut u8) {
    unsafe {
        Box::from_raw(ptr);
    }
}

extern "C" {
    // Accessors for fixtures and resources
    fn get_access_token() -> (*mut u8, u32);
    fn get_instance_url() -> (*mut u8, u32);
}
